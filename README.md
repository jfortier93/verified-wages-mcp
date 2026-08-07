# Verified Wages MCP

[![MCPize](https://mcpize.com/badge/@josh/verified-wages)](https://mcpize.com/mcp/verified-wages)

Current, source-cited US minimum wage, tipped wage, and FLSA overtime constants for AI agents. Federal + 50 states + DC + territories.

## Connect via MCPize

Use this MCP server instantly with no local installation:

```bash
npx -y mcpize connect @josh/verified-wages --client claude
```

Or connect at: **https://mcpize.com/mcp/verified-wages**

## Why this exists

As of five weeks ago, every frozen-weights model confidently believes Alaska's minimum wage is $13.00. It is $14.00 (July 1, 2026). Oregon and DC moved the same day; Florida moves again September 30. Wage rates change on chaotic sub-schedules, wage-and-hour suits are the most common employment litigation small businesses face, and agents doing HR or payroll work need the current number with a source — not a confident recollection of last year's.

Every response carries its DOL primary source, an as-of date, and a last-verified date. The server refuses rather than guesses.

## Tools (7, all read-only)

- `get_minimum_wage(state)` - current rate, regional splits, coverage quirks, scheduled changes
- `get_tipped_minimum(state)` - minimum cash wage, max tip credit, tipped-employee definition
- `wage_floor_check(state, hourly_rate, tipped?)` - informational comparison against the applicable floor
- `list_scheduled_changes()` - every future statutory change in the dataset, sorted by date
- `federal_flsa_basics()` - the $7.25 floor, $2.13 tipped cash minimum, overtime rule
- `states_at_federal_floor()` - which states exceed, match, or lack a state minimum
- `data_provenance()` - how and when every number was verified

## Example

```
get_minimum_wage("AK")
```

```json
{
  "jurisdiction": "Alaska",
  "state_minimum_hourly": 14.00,
  "note": "Increased from 13.00 effective 2026-07-01; daily OT after 8h; not applicable <4 employees",
  "source": "DOL WHD State Minimum Wage Laws, dol.gov/agencies/whd/minimum-wage/state (updated 2026-07-01)",
  "last_verified": "2026-08-06"
}
```

## Verification discipline

Two-pass verification against independent DOL documents (the consolidated state table and the tipped-employee table, both revised 2026-07-01), cross-checked against commercial compilations. Data is re-verified quarterly and within 7 days of official changes. Scope: state/territory floors only — city and county ordinances are excluded in v1 and may set higher rates.

## Run

```bash
pip install "mcp>=2.0"
python server.py
```

Tests: `python test_server.py` - hand-computed fixtures against the DOL tables, including all July 1 movers.

## Pricing (hosted)

- Free tier: 50 requests/month
- Then $0.01 per request, metered
- Or run locally free forever (MIT)

## Compliance posture

Educational reference only - **not legal advice**. State labor offices are authoritative. Exemptions, youth/training wages, and small-employer carve-outs are noted where DOL notes them but not evaluated by the tools.