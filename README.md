# infinihash-kyt-mcp

MCP server for [Infinihash KYT](https://kyt.infinihash.com) — real-time blockchain transaction monitoring, sanctions screening, and SAR generation as MCP tools.

Gives any MCP-compatible agent (Claude Desktop, Cursor, Cline, automation pipelines) access to:

- **`kyt_screen_wallet`** — screen a wallet against OFAC SDN + 18.8K+ risk labels in under 200ms
- **`kyt_lookup_intel`** — get known intel tags for an address (no full screen)
- **`kyt_recent_screenings`** — what your org has been screening
- **`kyt_create_case`** — open a compliance case from a risky screening
- **`kyt_list_cases`** — list open / SAR-pending / closed cases
- **`kyt_get_case`** — fetch one case with evidence notes
- **`kyt_add_case_note`** — append investigation notes to the audit trail
- **`kyt_generate_sar`** — render a FinCEN-aligned SAR draft
- **`kyt_stats`** — coverage stats (per-source breakdown)
- **`kyt_health`** — backend health probe

## Install

```bash
uvx infinihash-kyt-mcp
```

Or:

```bash
pip install infinihash-kyt-mcp
```

## Get an API key

Free tier — 100 screenings/month, no credit card required, key live in <60 seconds:

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
Screen wallet 0x722122dF12D4e14e13Ac3b6895a86e84145b6967 — is it sanctioned?

Open a case for the Tornado Cash address I just screened.

Generate a SAR draft for case <id> and email me a summary of what to include.

What labels do we have on 0x... — quick check, no full screen.
```

## Why KYT over alternatives

- **Published pricing** — no "contact sales" — Free $0, Starter $49/mo (500 screenings), Pro $199/mo (3,000 screenings)
- **Source transparency** — every label tiered (T1 OFAC, T2 threat intel, T3 on-chain, T4 community) and source-attributed at [/trust](https://kyt.infinihash.com/kyt/trust)
- **Self-serve in minutes** — API key in under a minute, no procurement cycle
- **Sub-200ms screens** — fast-path cache returns sanctioned wallets in milliseconds

Compare honestly vs TRM Labs + Chainalysis Reactor Lite: <https://kyt.infinihash.com/kyt/compare>

## Compliance note

KYT is a decision-support tool, not a SAR filing service. Your organisation remains solely responsible for SAR submissions via the [BSA E-Filing System](https://bsaefiling.fincen.treas.gov/) and for all regulatory determinations.

## Links

- API docs: <https://kyt.infinihash.com/docs>
- Trust Center: <https://kyt.infinihash.com/kyt/trust>
- Compare: <https://kyt.infinihash.com/kyt/compare>
- Support: <mailto:support@infinihash.com>

MIT licensed.
