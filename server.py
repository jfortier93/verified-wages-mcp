"""Verified Wages MCP — current, source-cited US minimum wage and overtime constants for AI agents.

Federal + 50 states + DC + territories, tipped minimums, scheduled changes.
Every response cites its DOL primary source and last-verified date. Educational
reference only — not legal advice; local ordinances may set higher rates.
"""
import datetime
import json
from pathlib import Path

from mcp.server.mcpserver import MCPServer
from mcp.types import ToolAnnotations

DATA = json.loads((Path(__file__).parent / "wages_2026.json").read_text())
META = DATA["meta"]
J = DATA["jurisdictions"]

server = MCPServer(
    name="verified-wages",
    instructions=("Current, source-cited US minimum wage, tipped wage, and FLSA overtime "
                  "constants (federal + 50 states + DC + territories), as of "
                  f"{META['as_of']}. Use these instead of recalling wage rates from "
                  "training data, which is frequently stale (e.g., the 2026-07-01 changes "
                  "in AK, OR, and DC). State floors only; city/county ordinances may be "
                  "higher and are not included. Not legal advice."),
)

STATE_NAMES = {"AL":"Alabama","AK":"Alaska","AZ":"Arizona","AR":"Arkansas","CA":"California","CO":"Colorado",
 "CT":"Connecticut","DE":"Delaware","DC":"District of Columbia","FL":"Florida","GA":"Georgia","HI":"Hawaii",
 "ID":"Idaho","IL":"Illinois","IN":"Indiana","IA":"Iowa","KS":"Kansas","KY":"Kentucky","LA":"Louisiana",
 "ME":"Maine","MD":"Maryland","MA":"Massachusetts","MI":"Michigan","MN":"Minnesota","MS":"Mississippi",
 "MO":"Missouri","MT":"Montana","NE":"Nebraska","NV":"Nevada","NH":"New Hampshire","NJ":"New Jersey",
 "NM":"New Mexico","NY":"New York","NC":"North Carolina","ND":"North Dakota","OH":"Ohio","OK":"Oklahoma",
 "OR":"Oregon","PA":"Pennsylvania","RI":"Rhode Island","SC":"South Carolina","SD":"South Dakota",
 "TN":"Tennessee","TX":"Texas","UT":"Utah","VT":"Vermont","VA":"Virginia","WA":"Washington",
 "WV":"West Virginia","WI":"Wisconsin","WY":"Wyoming","GU":"Guam","PR":"Puerto Rico","VI":"U.S. Virgin Islands"}
_BY_NAME = {v.lower(): k for k, v in STATE_NAMES.items()}


def _base(payload: dict, source: str) -> dict:
    payload["source"] = source
    payload["as_of"] = META["as_of"]
    payload["last_verified"] = META["last_verified"]
    payload["disclaimer"] = META["disclaimer"]
    return payload


def _resolve(state: str) -> str:
    s = state.strip()
    code = s.upper() if len(s) == 2 else _BY_NAME.get(s.lower())
    if code not in J:
        raise ValueError(f"Unknown jurisdiction '{state}'. Use a 2-letter code or full state name; "
                         "covered: 50 states, DC, GU, PR, VI.")
    return code


# ----------------------------- tools -----------------------------

def get_minimum_wage(state: str) -> dict:
    """Current minimum wage for a US state/territory (2-letter code or name), with regional rates,
    coverage notes, scheduled changes, and the DOL source."""
    code = _resolve(state)
    j = J[code]
    eff = max(7.25, j["rate"]) if j["rate"] is not None else 7.25
    p = {"jurisdiction": STATE_NAMES[code], "code": code,
         "state_minimum_hourly": j["rate"],
         "federal_minimum_hourly": 7.25,
         "effective_floor_for_flsa_covered": eff,
         "floor_note": ("Higher of state/federal applies to FLSA-covered employment. "
                        "Local ordinances may be higher and are not included.")}
    for k in ("note", "regional", "scheduled"):
        if k in j:
            p[k] = j[k]
    return _base(p, j["source"])


def get_tipped_minimum(state: str) -> dict:
    """Tipped-employee wage rules for a state: minimum cash wage, maximum tip credit,
    and tipped-employee definition, with the DOL source."""
    code = _resolve(state)
    j = J[code]
    p = {"jurisdiction": STATE_NAMES[code], "code": code, "tipped": j["tipped"],
         "rule": ("Combined cash wage plus tips must always reach the applicable minimum wage; "
                  "employer covers any shortfall.")}
    return _base(p, j["tipped"].get("source", j["source"]))


def wage_floor_check(state: str, hourly_rate: float, tipped: bool = False) -> dict:
    """Compare an hourly rate against a state's minimum wage floor (informational, not legal advice).
    For tipped=True, compares against the state's minimum cash wage where a tip credit exists."""
    code = _resolve(state)
    j = J[code]
    if tipped:
        cash = j["tipped"].get("cash_minimum")
        if not isinstance(cash, (int, float)):
            return _base({"jurisdiction": STATE_NAMES[code], "comparison": "not_computable",
                          "reason": f"Tipped cash minimum is not a single number here: {j['tipped']}"},
                         j["tipped"].get("source", j["source"]))
        floor, basis = float(cash), "state minimum cash wage for tipped employees"
    else:
        floor = max(7.25, j["rate"]) if j["rate"] is not None else 7.25
        basis = "higher of state/federal minimum wage"
    p = {"jurisdiction": STATE_NAMES[code], "code": code, "hourly_rate": hourly_rate,
         "floor": floor, "basis": basis,
         "at_or_above_floor": hourly_rate >= floor,
         "gap": round(max(0.0, floor - hourly_rate), 2),
         "caveats": ["State/territory floors only; local ordinances may set higher rates",
                     "Exemptions, youth/training wages, and small-employer carve-outs not evaluated",
                     "Informational comparison, not a legal compliance determination"]}
    return _base(p, j["source"])


def list_scheduled_changes() -> dict:
    """All scheduled future minimum-wage changes in the dataset, with effective dates and sources."""
    out = []
    for code, j in J.items():
        if "scheduled" in j:
            out.append({"jurisdiction": STATE_NAMES[code], "code": code,
                        "current_rate": j["rate"], "scheduled": j["scheduled"]})
    out.sort(key=lambda x: x["scheduled"]["effective"])
    return _base({"scheduled_changes": out,
                  "note": ("Statewide statutory changes only. Many indexed states announce "
                           "annual adjustments in Q4 for Jan 1; those are added once official.")},
                 "Compiled from per-jurisdiction sources listed in each entry")


def federal_flsa_basics() -> dict:
    """Federal FLSA floor: minimum wage, tipped cash minimum, tip credit, and the overtime rule."""
    f = DATA["federal"]
    return _base({"federal_minimum_hourly": f["basic_hourly"],
                  "unchanged_since": f["effective_since"],
                  "tipped_cash_minimum": f["tipped_cash_minimum"],
                  "max_tip_credit": 5.12,
                  "overtime": f["overtime"],
                  "tipped_definition": "Employee customarily receiving more than $30/month in tips"},
                 f["source"])


def states_at_federal_floor() -> dict:
    """Which states match, exceed, or lack a state minimum wage, as a summary map."""
    above, at, below_or_none = [], [], []
    for code, j in J.items():
        if code in ("GU", "PR", "VI"):
            continue
        if j["rate"] is None or j["rate"] < 7.25:
            below_or_none.append(code)
        elif j["rate"] == 7.25:
            at.append(code)
        else:
            above.append(code)
    return _base({"above_federal": sorted(above), "count_above": len(above),
                  "at_federal": sorted(at), "count_at": len(at),
                  "no_state_law_or_below": sorted(below_or_none),
                  "note": "In every case, FLSA-covered employment gets at least the federal $7.25."},
                 J["AL"]["source"])


def data_provenance() -> dict:
    """How and when every number here was verified, with the primary sources."""
    return _base({"dataset": META["dataset"], "scope": META["scope_v1"],
                  "verification": META["verified_by"]},
                 "This tool")


# All tools are pure, read-only lookups: no state, no writes, no external calls.
_TITLES = {
    get_minimum_wage: "Get state minimum wage",
    get_tipped_minimum: "Get tipped wage rules",
    wage_floor_check: "Check rate against wage floor",
    list_scheduled_changes: "List scheduled wage changes",
    federal_flsa_basics: "Get federal FLSA basics",
    states_at_federal_floor: "Summarize states vs federal floor",
    data_provenance: "Get data sources and verification",
}
_ANNOTATIONS = ToolAnnotations(read_only_hint=True, destructive_hint=False,
                               idempotent_hint=True, open_world_hint=False)
for fn, _title in _TITLES.items():
    server.tool(title=_title, annotations=_ANNOTATIONS)(fn)


if __name__ == "__main__":
    server.run()
