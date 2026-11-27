"""kyt_screen_wallet must read the fields the KYT engine actually returns.

The fixtures in tests/fixtures/ were rendered by clearauthority-kyt's own
ScreenResponse serializer (app/schemas/screen.py, branch audit/2026-11-fixes)
and their key set matches the live schema at
https://kyt.infinihash.com/api/v1/openapi.json (components.schemas.ScreenResponse)
as of 2026-11-26. Earlier versions of the server read `score`, `signals`,
`entity`, `address` and `ai_narrative`, none of which exist in that response,
so every MCP screen came back with those fields null.
"""
import asyncio
import json
import pathlib

import pytest

from infinihash_kyt_mcp import server

FIXTURES = pathlib.Path(__file__).parent / "fixtures"

# components.schemas.ScreenResponse.properties from the live OpenAPI document.
LIVE_SCREEN_RESPONSE_FIELDS = {
    "action", "api_key_id", "attribution", "chain", "completed_at", "coverage",
    "created_at", "crosschain_hops", "entity_confidence", "entity_name",
    "entity_source", "events", "explanation", "exposure_breakdown", "flags", "id",
    "list_as_of", "narrative", "risk_level", "risk_score", "screening_incomplete",
    "status", "trace", "type", "value", "verdict",
}


def _load(name):
    return json.loads((FIXTURES / name).read_text())


class FakeAPI:
    def __init__(self, responses):
        self.responses = list(responses)
        self.calls = []

    async def __call__(self, method, path, *, body=None, auth=True):
        self.calls.append((method, path, body))
        return self.responses.pop(0)


def _screen(monkeypatch, responses, **args):
    fake = FakeAPI(responses)
    monkeypatch.setattr(server, "_request", fake)
    monkeypatch.setattr(server, "_POLL_DELAYS", (0, 0, 0))
    out = asyncio.run(server.call_tool("kyt_screen_wallet", {"address": "0xabc", **args}))
    return json.loads(out[0].text), fake


@pytest.mark.parametrize("name", ["screen_complete_sanctioned.json", "screen_queued.json"])
def test_fixtures_have_live_schema_shape(name):
    assert set(_load(name)) == LIVE_SCREEN_RESPONSE_FIELDS


def test_complete_screening_maps_score_signals_entity_and_narrative(monkeypatch):
    fx = _load("screen_complete_sanctioned.json")
    slim, fake = _screen(monkeypatch, [fx])

    assert fake.calls == [("POST", "/screen", {"address": "0xabc"})]
    assert slim["score"] == 100
    assert slim["risk_level"] == "critical"
    assert slim["action"] == "block_report"
    assert slim["verdict"] == "flagged"
    assert slim["signals"] == ["direct_sanctions_match"]
    assert slim["entity"] == "Lazarus Group (Ronin Bridge exploiter)"
    assert slim["address"] == fx["value"]
    assert slim["ai_summary"].startswith("BLOCKED:")
    assert slim["score_explanation"].startswith("Score 100 (critical)")
    assert slim["exposure_breakdown"]["receiving"]["exchange"]["pct"] == 75.0
    assert slim["list_as_of"] == fx["list_as_of"]
    assert "note" not in slim


def test_signals_fall_back_to_event_names_when_flags_missing(monkeypatch):
    fx = _load("screen_complete_sanctioned.json")
    fx["flags"] = None
    slim, _ = _screen(monkeypatch, [fx])
    assert slim["signals"] == ["direct_sanctions_match"]


def test_chain_override_is_sent(monkeypatch):
    _, fake = _screen(monkeypatch, [_load("screen_complete_sanctioned.json")], chain="BASE")
    assert fake.calls[0] == ("POST", "/screen", {"address": "0xabc", "chain": "BASE"})


def test_queued_screening_is_polled_until_complete(monkeypatch):
    queued = _load("screen_queued.json")
    done = _load("screen_complete_sanctioned.json")
    slim, fake = _screen(monkeypatch, [queued, queued, done])

    assert [c[:2] for c in fake.calls] == [
        ("POST", "/screen"),
        ("GET", f"/screen/{queued['id']}"),
        ("GET", f"/screen/{queued['id']}"),
    ]
    assert slim["status"] == "complete"
    assert slim["score"] == 100


def test_still_queued_after_polling_says_so(monkeypatch):
    queued = _load("screen_queued.json")
    slim, fake = _screen(monkeypatch, [queued] * 4)

    assert len(fake.calls) == 4  # POST + 3 polls (patched _POLL_DELAYS)
    assert slim["status"] == "queued"
    assert slim["score"] is None
    assert slim["signals"] == []
    assert "still running" in slim["note"]
