from __future__ import annotations
import statistics 
from gates import Flag 

def _funders(entities):
    return {e["parent"] for e in entities.values() if e["parent"]}

def retention_anomaly(entities, k=3.0):
    funders = _funders(entities)
    rows = []
    for e in entities.values():
        if e["id"] not in funders:
            continue 
        r = e["received"]
        hold = (r - e["paid_out"]) / r if r else 0 
        rows.append((e, hold))
    if len(rows) < 3:
        return []
    holds = [h for _, h in rows]
    med = statistics.median(holds)
    mad = statistics.median([abs(h - med) for h in holds]) or 1e-9
    flags = []
    for e, h in rows:
        z = (h - med) / mad
        if z > k:
            flags.append(Flag(e["id"], "retention_anomaly", min(1.0, z / 8), f"holds {h * 100:.0f}% of inflow vs peer median {med * 100:.0f}%"))
    return flags 
def run_analyzer(entities):
    return retention_anomaly(entities)
