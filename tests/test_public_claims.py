"""Audit 2026-11: public copy in the README, package metadata and tool
descriptions must match the pricing freeze (2026-09-23) and avoid
unsubstantiated claims.

- Pricing freeze: Starter $49/mo = 400 KYT screenings, Pro $199/mo = 2,400.
  The README said 500 / 3,000.
- No latency claims ("under 200ms", "Sub-200ms", "<200ms"): none is
  substantiated.
- No hard-coded label counts ("18.8K+", "~29K+"): they drift; point at
  /api/v1/coverage instead.
- No "real-time" wording.
- Tornado Cash was delisted by OFAC on 2025-03-21; it must not be the
  "is it sanctioned?" example.
"""
import pathlib
import re

ROOT = pathlib.Path(__file__).resolve().parent.parent
FILES = {
    "README.md": ROOT / "README.md",
    "pyproject.toml": ROOT / "pyproject.toml",
    "server.py": ROOT / "src" / "infinihash_kyt_mcp" / "server.py",
    "server.json": ROOT / "server.json",
    "smithery.yaml": ROOT / "smithery.yaml",
}
TEXT = {k: p.read_text() for k, p in FILES.items()}


def test_pricing_matches_freeze():
    readme = TEXT["README.md"]
    assert "Starter $49/mo (400 screenings)" in readme
    assert "Pro $199/mo (2,400 screenings)" in readme
    assert "500 screenings" not in readme
    assert "3,000 screenings" not in readme


def test_no_latency_claims():
    pat = re.compile(r"(under|sub-?|<)\s*200\s*ms", re.I)
    for name, s in TEXT.items():
        assert not pat.search(s), f"{name} makes a latency claim"


def test_no_hardcoded_label_counts():
    for name, s in TEXT.items():
        assert "18.8K" not in s and "29K" not in s, f"{name} hard-codes a label count"


def test_no_real_time_wording():
    for name, s in TEXT.items():
        assert not re.search(r"real-?time", s, re.I), f"{name} says real-time"


def test_sanctioned_example_is_not_tornado_cash():
    readme = TEXT["README.md"]
    assert "0x722122dF12D4e14e13Ac3b6895a86e84145b6967 — is it sanctioned" not in readme
    assert "Tornado Cash address" not in readme
    assert "0x098B716B8Aaf21512996dC57EB0615e2383E2f96 — is it sanctioned?" in readme
