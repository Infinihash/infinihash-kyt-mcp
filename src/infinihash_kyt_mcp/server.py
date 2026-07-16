"""
Infinihash KYT MCP Server

Exposes the Infinihash KYT blockchain-transaction-monitoring API as MCP tools
so any MCP-compatible agent (Claude Desktop, Cursor, automation pipelines)
can screen wallets, open compliance cases, and generate SAR drafts without
writing any HTTP glue.

Tool surface (v0.1.0):
  kyt_screen_wallet      — screen a wallet address against OFAC + risk labels
  kyt_lookup_intel       — get all known intel labels for an address
  kyt_recent_screenings  — list recent screenings for your org
  kyt_create_case        — open a compliance case from a risky screening
  kyt_list_cases         — list open / SAR-pending / closed cases
  kyt_get_case           — fetch a single case + its notes
  kyt_add_case_note      — add an evidence note to a case
  kyt_generate_sar       — render a FinCEN-aligned SAR draft for a case
  kyt_stats              — coverage stats (labels per source tier)
  kyt_health             — backend health probe

Environment variables:
  KYT_API_KEY   — your KYT API key (required, X-API-Key header)
  KYT_BASE_URL  — API base (default: https://kyt.infinihash.com/api/v1)
"""

from __future__ import annotations

import json
import os
from urllib.parse import quote
from typing import Any

import httpx
from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import TextContent, Tool

BASE_URL = os.environ.get("KYT_BASE_URL", "https://kyt.infinihash.com/api/v1").rstrip("/")
API_KEY  = os.environ.get("KYT_API_KEY", "")

app = Server("infinihash-kyt")


def _p(segment: str) -> str:
    """URL-encode a single path/query segment.

    Path & query parameters (wallet address, case_id, status) are
    attacker-influenced. Without encoding, a value containing '/', '?', '#',
    '&' or '..' rewrites the request URL and can redirect the call to an
    unintended endpoint or inject extra query params (path / query injection).
    quote(..., safe="") percent-encodes every reserved character so the value
    always stays a single, inert segment.
    """
    return quote(str(segment), safe="")


# ── Helpers ───────────────────────────────────────────────────────────────────

def _headers(require_auth: bool = True) -> dict:
    h = {"Content-Type": "application/json"}
    if API_KEY:
        # KYT backend accepts X-API-Key OR Bearer; send both for resilience.
        h["X-API-Key"] = API_KEY
        h["Authorization"] = f"Bearer {API_KEY}"
    elif require_auth:
        raise ValueError(
            "KYT_API_KEY is not set. Get one free at https://kyt.infinihash.com — "
            "100 screenings/month, no credit card required."
        )
    return h


async def _request(method: str, path: str, *, body: dict | None = None, auth: bool = True) -> Any:
    async with httpx.AsyncClient(timeout=60) as client:
        r = await client.request(
            method,
            f"{BASE_URL}{path}",
            headers=_headers(auth),
            json=body,
        )
        r.raise_for_status()
        # Some endpoints (SAR text) return text/plain
        ctype = r.headers.get("content-type", "")
        if "application/json" in ctype:
            return r.json()
        return r.text


def _ok(data: Any) -> list[TextContent]:
    if isinstance(data, str):
        return [TextContent(type="text", text=data)]
    return [TextContent(type="text", text=json.dumps(data, indent=2, default=str))]


def _err(msg: str) -> list[TextContent]:
    return [TextContent(type="text", text=f"Error: {msg}")]


# ── Tool definitions ──────────────────────────────────────────────────────────

TOOLS = [
    Tool(
        name="kyt_screen_wallet",
        description=(
            "Screen a single wallet address against OFAC SDN, stablecoin freezes, "
            "ScamSniffer threat intel, and 18.8K+ community-reviewed labels. Returns a "
            "0-100 risk score, matched signals, exposure breakdown, an AI-generated "
            "investigation summary, and a recommended action (clear / review / block). "
            "Use this BEFORE settling on-chain — sanctioned wallets are caught in <200ms "
            "from the fast-path cache. Chain is auto-detected from the address format."
        ),
        inputSchema={
            "type": "object",
            "properties": {
                "address": {
                    "type": "string",
                    "description": "Wallet address. EVM (0x...), Bitcoin (1.../bc1...), Tron (T...), Solana, etc. — chain is auto-detected.",
                },
                "chain": {
                    "type": "string",
                    "description": "Optional. Override auto-detection. Values: ETH | BTC | TRX | SOL | POLYGON | BASE | ARB | OP | AVAX | BSC | auto",
                    "default": "auto",
                },
            },
            "required": ["address"],
        },
    ),
    Tool(
        name="kyt_lookup_intel",
        description=(
            "Look up known intelligence labels for an address without running a full "
            "screen. Returns tiered labels (T1 OFAC SDN, T2 threat intel, T3 on-chain "
            "freezes, T4 community-reviewed) with source attribution. Cheaper than a "
            "full screen — use when you only need to know whether an address is known."
        ),
        inputSchema={
            "type": "object",
            "properties": {
                "address": {"type": "string", "description": "Wallet address to look up."},
            },
            "required": ["address"],
        },
    ),
    Tool(
        name="kyt_recent_screenings",
        description=(
            "List recent screenings performed by your organisation. Useful for catching "
            "up on what teammates or automated pipelines have been screening. Returns "
            "address, chain, score, risk level, and timestamp per row."
        ),
        inputSchema={
            "type": "object",
            "properties": {
                "limit": {
                    "type": "integer",
                    "description": "Max rows to return (default 20, max 200).",
                    "default": 20,
                },
            },
        },
    ),
    Tool(
        name="kyt_create_case",
        description=(
            "Open a compliance case from a flagged screening. A case bundles evidence, "
            "notes, and the audit trail you'll need if you escalate to a SAR. Pass the "
            "address that triggered the alert; the case is opened under your org with "
            "status='open' and tied to the most recent screening of that address."
        ),
        inputSchema={
            "type": "object",
            "properties": {
                "address": {"type": "string", "description": "Address that triggered the case."},
                "chain": {"type": "string", "description": "Chain code (e.g. ethereum, bitcoin, tron)."},
                "notes": {"type": "string", "description": "Optional initial note describing why the case was opened."},
            },
            "required": ["address"],
        },
    ),
    Tool(
        name="kyt_list_cases",
        description=(
            "List your organisation's compliance cases. Filter by status to find cases "
            "needing review or escalation. Each case includes id, address, chain, "
            "risk level, status, stage, and timestamps."
        ),
        inputSchema={
            "type": "object",
            "properties": {
                "status": {
                    "type": "string",
                    "description": "Optional filter: open | sar_pending | closed | all (default all).",
                    "enum": ["open", "sar_pending", "closed", "all"],
                },
                "limit": {"type": "integer", "description": "Max rows (default 50).", "default": 50},
            },
        },
    ),
    Tool(
        name="kyt_get_case",
        description="Fetch a single case by ID, including evidence notes and screening linkage.",
        inputSchema={
            "type": "object",
            "properties": {
                "case_id": {"type": "string", "description": "Case UUID."},
            },
            "required": ["case_id"],
        },
    ),
    Tool(
        name="kyt_add_case_note",
        description=(
            "Append an investigation note to a case. Notes are timestamped, attributed, "
            "and form part of the audit trail you'd hand to a regulator. Use this to "
            "document transaction hashes, counterparty findings, or analyst rationale."
        ),
        inputSchema={
            "type": "object",
            "properties": {
                "case_id": {"type": "string", "description": "Case UUID."},
                "note": {"type": "string", "description": "Free-form investigation note."},
            },
            "required": ["case_id", "note"],
        },
    ),
    Tool(
        name="kyt_generate_sar",
        description=(
            "Generate a FinCEN-aligned Suspicious Activity Report draft for a case. "
            "Returns the SAR as plain text ready for review and submission via the BSA "
            "E-Filing System. Compliance Officer remains responsible for review + "
            "filing — this is decision-support, not auto-filing."
        ),
        inputSchema={
            "type": "object",
            "properties": {
                "case_id": {"type": "string", "description": "Case UUID."},
            },
            "required": ["case_id"],
        },
    ),
    Tool(
        name="kyt_stats",
        description=(
            "Return KYT coverage stats: total labeled addresses (~29K+), per-tier "
            "breakdown (T1 OFAC, T2 threat intel, T3 on-chain freezes, T4 community), "
            "data sources, and update cadence. Useful for compliance documentation."
        ),
        inputSchema={"type": "object", "properties": {}},
    ),
    Tool(
        name="kyt_health",
        description="Backend health probe. Returns 'ok' when the KYT screening engine is responsive.",
        inputSchema={"type": "object", "properties": {}},
    ),
]


# ── Routing ───────────────────────────────────────────────────────────────────

@app.list_tools()
async def list_tools() -> list[Tool]:
    return TOOLS


@app.call_tool()
async def call_tool(name: str, arguments: dict) -> list[TextContent]:
    try:
        if name == "kyt_screen_wallet":
            body = {"address": arguments["address"]}
            chain = arguments.get("chain")
            if chain and chain != "auto":
                body["chain"] = chain
            result = await _request("POST", "/screen", body=body)
            # Trim the response to the most useful fields for an agent
            slim = {
                "id": result.get("id"),
                "address": result.get("address"),
                "chain": result.get("chain"),
                "risk_level": result.get("risk_level"),
                "score": result.get("score"),
                "action": result.get("action") or result.get("recommend"),
                "signals": result.get("signals", []),
                "entity": result.get("entity"),
                "ai_summary": result.get("ai_narrative") or result.get("narrative"),
            }
            return _ok(slim)

        elif name == "kyt_lookup_intel":
            address = arguments["address"]
            result = await _request("GET", f"/intel/lookup/{_p(address)}")
            return _ok(result)

        elif name == "kyt_recent_screenings":
            limit = min(int(arguments.get("limit", 20)), 200)
            result = await _request("GET", f"/intel/recent-screenings?limit={limit}")
            return _ok(result)

        elif name == "kyt_create_case":
            body = {
                "address": arguments["address"],
                "chain": arguments.get("chain", "ethereum"),
            }
            if "notes" in arguments:
                body["notes"] = arguments["notes"]
            result = await _request("POST", "/cases", body=body)
            return _ok(result)

        elif name == "kyt_list_cases":
            status = arguments.get("status", "all")
            limit = int(arguments.get("limit", 50))
            qs = f"?limit={limit}"
            if status and status != "all":
                qs += f"&status={_p(status)}"
            result = await _request("GET", f"/cases{qs}")
            return _ok(result)

        elif name == "kyt_get_case":
            case_id = arguments["case_id"]
            result = await _request("GET", f"/cases/{_p(case_id)}")
            return _ok(result)

        elif name == "kyt_add_case_note":
            case_id = arguments["case_id"]
            body = {"note": arguments["note"]}
            result = await _request("POST", f"/cases/{_p(case_id)}/notes", body=body)
            return _ok(result)

        elif name == "kyt_generate_sar":
            case_id = arguments["case_id"]
            # /cases/{id}/sar returns text/plain SAR draft
            result = await _request("GET", f"/cases/{_p(case_id)}/sar")
            return _ok(result)

        elif name == "kyt_stats":
            result = await _request("GET", "/intel/stats", auth=bool(API_KEY))
            return _ok(result)

        elif name == "kyt_health":
            result = await _request("GET", "/health", auth=False)
            return _ok(result)

        else:
            return _err(f"Unknown tool: {name}")

    except httpx.HTTPStatusError as e:
        body = e.response.text[:400] if e.response is not None else ""
        return _err(f"HTTP {e.response.status_code}: {body}")
    except Exception as e:
        return _err(str(e))


# ── Entry point ───────────────────────────────────────────────────────────────

async def main() -> None:
    async with stdio_server() as (read_stream, write_stream):
        await app.run(read_stream, write_stream, app.create_initialization_options())


def run() -> None:
    import asyncio
    asyncio.run(main())


if __name__ == "__main__":
    run()
