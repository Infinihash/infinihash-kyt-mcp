"""Regression tests for #9702 — path/query params must be URL-encoded so a
value containing '/', '?', '#', '&' or '..' cannot break out of the intended
request path (path/query injection)."""
import importlib

server = importlib.import_module("infinihash_kyt_mcp.server")
_p = server._p


def test_encodes_path_breakout_characters():
    assert _p("a/b") == "a%2Fb"
    assert _p("a?b") == "a%3Fb"
    assert _p("a#b") == "a%23b"
    assert _p("../../secret") == "..%2F..%2Fsecret"
    assert _p("id&status=closed") == "id%26status%3Dclosed"


def test_leaves_legitimate_identifiers_untouched():
    # Unreserved chars (alnum, '-', '_', '.', '~') pass through unchanged.
    assert _p("0xAbC123") == "0xAbC123"
    uuid = "3fa85f64-5717-4562-b3fc-2c963f66afa6"
    assert _p(uuid) == uuid


def test_injected_path_param_stays_a_single_segment():
    malicious = "TXYZ/../cases/00000000-0000-0000-0000-000000000000"
    enc = _p(malicious)
    built = f"/intel/lookup/{enc}"
    assert "/" not in enc  # the param contributes zero raw slashes
    assert "/cases/" not in built  # cannot pivot to another route


def test_injected_status_query_cannot_add_params():
    built = f"/cases?limit=50&status={_p('open&admin=1')}"
    assert built == "/cases?limit=50&status=open%26admin%3D1"
    assert "&admin=1" not in built
