# infinihash-kyt-mcp

<!-- mcp-name: io.github.Infinihash/infinihash-kyt-mcp -->

MCP server for [Infinihash KYT](https://kyt.infinihash.com) — blockchain wallet screening, sanctions screening, case management and SAR drafts as MCP tools.

Gives any MCP-compatible agent (Claude Desktop, Cursor, Cline, automation pipelines) access to:

- **`kyt_screen_wallet`** — screen a wallet against sanctions lists (OFAC SDN, EU, UK, OpenSanctions crypto wallets) and Infinihash risk labels (current counts: [`/api/v1/coverage`](https://kyt.infinihash.com/api/v1/coverage))
- **`kyt_lookup_intel`** — get known intel tags for an address (no full screen)
- **`kyt_recent_screenings`** — what your org has been screening
- **`kyt_create_case`** — open a compliance case from a risky screening
- **`kyt_list_cases`** — list open / SAR-pending / closed cases
- **`kyt_get_case`** — fetch one case with evidence notes
- **`kyt_add_case_note`** — append investigation notes to the audit trail
- **`kyt_generate_sar`** — render a FinCEN-aligned SAR draft
- **`kyt_stats`** — coverage stats (per-source breakdown)
- **`kyt_health`** — backend health probe

## Hosted (no install)

Connect straight from Claude.ai, Claude Desktop, or any MCP client that supports remote servers:

- **URL:** `https://mcp.infinihash.com/mcp`. Sign in with your KYT API key when prompted (OAuth).
- **No key yet?** `https://mcp.infinihash.com/free/mcp` gives anonymous, basic sanctions screening.
- Claude Code: `claude mcp add --transport http infinihash-kyt https://mcp.infinihash.com/mcp`

The hosted server adds `preflight_payment`: call it before an agent sends crypto. It returns ALLOW, REVIEW or BLOCK plus an Ed25519-signed receipt you can keep for examiners (`verify_receipt` checks it; public key at `/.well-known/kyt-receipt-key`).

## Install (local, stdio)

```bash
uvx infinihash-kyt-mcp
```

Or:

```bash
pip install infinihash-kyt-mcp
```

## Get an API key

Free tier — 100 screenings/month, no credit card required:

→ <https://kyt.infinihash.com/kyt/settings/api-keys>

## Claude Desktop config

Add to `~/Library/Application Support/Claude/claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "infinihash-kyt": {
      "command": "uvx",
      "args": ["infinihash-kyt-mcp"],
      "env": {
        "KYT_API_KEY": "kyt_your_key_here"
      }
    }
  }
}
```

## Cursor / Cline

Same JSON, different file. See the [docs](https://kyt.infinihash.com/docs).

## Example prompts after install

```
Screen wallet 0x098B716B8Aaf21512996dC57EB0615e2383E2f96 — is it sanctioned?

Open a case for the address I just screened.

Generate a SAR draft for case <id> and email me a summary of what to include.

What labels do we have on 0x... — quick check, no full screen.
```

## Why KYT over alternatives

- **Published pricing** — Free $0 (100 screenings/mo), Starter $49/mo (400 screenings), Pro $199/mo (2,400 screenings); $0.15 per screening over the included amount on Starter and Pro. Enterprise: contact us
- **Source transparency** — every label tiered (T1 OFAC, T2 threat intel, T3 on-chain, T4 community) and source-attributed at [/trust](https://kyt.infinihash.com/kyt/trust)
- **Self-serve** — create an API key from the dashboard, no procurement cycle

Compare honestly vs TRM Labs + Chainalysis Reactor Lite: <https://kyt.infinihash.com/kyt/compare>

## Compliance note

KYT is a decision-support tool, not a SAR filing service. Your organisation remains solely responsible for SAR submissions via the [BSA E-Filing System](https://bsaefiling.fincen.treas.gov/) and for all regulatory determinations.

## Links

- API docs: <https://kyt.infinihash.com/docs>
- Trust Center: <https://kyt.infinihash.com/kyt/trust>
- Compare: <https://kyt.infinihash.com/kyt/compare>
- Support: <mailto:support@infinihash.com>

MIT licensed.
