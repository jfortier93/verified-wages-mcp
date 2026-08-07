"""Hand-computed fixtures against the DOL July 1, 2026 tables."""
import asyncio
import server as s

def approx(a, b, tol=0.001):
    assert abs(a - b) <= tol, f"expected {b}, got {a}"

# July 1 movers — the wedge cases
r = s.get_minimum_wage("AK")
approx(r["state_minimum_hourly"], 14.00); assert "2026-07-01" in r["note"]
r = s.get_minimum_wage("District of Columbia")
approx(r["state_minimum_hourly"], 18.40)
r = s.get_minimum_wage("OR")
approx(r["state_minimum_hourly"], 15.55); approx(r["regional"]["Portland Metro"], 16.80); approx(r["regional"]["Non-urban counties"], 14.55)

# Scheduled changes: FL Sept 30 first, MI Jan 1 second
sc = s.list_scheduled_changes()["scheduled_changes"]
assert sc[0]["code"] == "FL" and sc[0]["scheduled"]["effective"] == "2026-09-30"; approx(sc[0]["scheduled"]["rate"], 15.00)
assert sc[1]["code"] == "MI" and sc[1]["scheduled"]["effective"] == "2027-01-01"

# No-state-law + sub-federal states resolve to federal floor
r = s.get_minimum_wage("Alabama")
assert r["state_minimum_hourly"] is None; approx(r["effective_floor_for_flsa_covered"], 7.25)
r = s.get_minimum_wage("GA")
approx(r["state_minimum_hourly"], 5.15); approx(r["effective_floor_for_flsa_covered"], 7.25)

# Tipped: full-wage states, credit states, federal-scheme states
assert "full state minimum" in s.get_tipped_minimum("CA")["tipped"]["cash_minimum"]
t = s.get_tipped_minimum("FL")["tipped"]; approx(t["max_tip_credit"], 3.02); approx(t["cash_minimum"], 10.98)
t = s.get_tipped_minimum("TX")["tipped"]; approx(t["cash_minimum"], 2.13)
t = s.get_tipped_minimum("CT")["tipped"]; approx(t["hotel_restaurant_cash"], 6.38); approx(t["bartender_cash"], 8.23)

# Floor checks, hand-computed
c = s.wage_floor_check("MO", 14.50); assert not c["at_or_above_floor"]; approx(c["gap"], 0.50); approx(c["floor"], 15.00)
c = s.wage_floor_check("AL", 7.25); assert c["at_or_above_floor"]; approx(c["floor"], 7.25)
c = s.wage_floor_check("FL", 11.00, tipped=True); assert c["at_or_above_floor"]; approx(c["floor"], 10.98)
c = s.wage_floor_check("NY", 10.00, tipped=True); assert c["comparison"] == "not_computable"

# Summary map: 13 states at exactly 7.25; 7 at none-or-below (5 no-law + GA + WY)
m = s.states_at_federal_floor()
assert m["count_at"] == 13, m["at_federal"]
assert len(m["no_state_law_or_below"]) == 7, m["no_state_law_or_below"]

# Federal + provenance + disclaimer on every payload
f = s.federal_flsa_basics(); approx(f["federal_minimum_hourly"], 7.25); approx(f["tipped_cash_minimum"], 2.13)
for resp in (r, t, c, m, f, s.data_provenance()):
    assert resp.get("disclaimer") or "source" in resp

tools = asyncio.run(s.server.list_tools())
names = sorted(x.name for x in tools)
assert len(names) == 7, names
assert all(x.annotations.read_only_hint for x in tools)
print("ALL TESTS PASSED")
print("Registered tools:", ", ".join(names))
