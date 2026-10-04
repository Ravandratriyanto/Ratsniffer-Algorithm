from __future__ import annotations
import random 
from gates import Flag 

SKIM_TOL = 0.08
DELIVERY_TOL = 0.02
MARKET_RETURN_HI = 0.25
def attest(run, coverage=1.0, rng=None, ids=None):
    rng = rng or random.Random()
    att = {}
    for n in run["nodes"]:
        covered = (n["id"] in ids) if ids is not None else (rng.random() <= coverage)
        if covered:
            att[n["id"]] = {"confirmed_delivery": n["trueDelivered"], "skim": n["diverted"],
                            "real_value": n["received"] * (1 - n.get("phantom", 0))}
    return att

def reconcile(run, attest_map):
    flags = []
    for n in run["nodes"]:
        a = attest_map.get(n["id"])
        if not a:
            continue
        r = n["received"] or 1.0
        skim_frac = a["skim"] / r
        if skim_frac > SKIM_TOL:
            flags.append(Flag(n["id"], "oracle_skim", min(1.0, skim_frac),
                              f"audit: {skim_frac * 100:.0f}% of inflow unaccounted"))
        d = n["delivered"] or 0.0
        if d and (d - a["confirmed_delivery"]) / d > DELIVERY_TOL:
            flags.append(Flag(n["id"], "oracle_ghost", min(1.0, (d - a["confirmed_delivery"]) / d),
                              f"reported {d:.0f} delivered, confirmed {a['confirmed_delivery']:.0f}"))
        rv = a.get("real_value")
        if rv is not None and (n["received"] - rv) / r > DELIVERY_TOL:
            gap = (n["received"] - rv) / r
            flags.append(Flag(n["id"], "oracle_phantom", min(1.0, gap),
                              f"{gap * 100:.0f}% of invoiced goods don't exist"))
    return flags

def wealth_reconciliation(entities):
    flags = []
    for e in entities.values():
        for src, amount, ret, linked in e.get("external_income", []):
            if linked:
                flags.append(Flag(e["id"], "laundered_wealth", 0.9,
                    f"outside income from connected party {src}"))
            elif ret is not None and ret > MARKET_RETURN_HI:
                flags.append(Flag(e["id"], "implausible_returns",
                    min(1.0, ret / MARKET_RETURN_HI - 1),
                    f"{ret*100:.0f}% return vs market ceiling {MARKET_RETURN_HI*100:.0f}%"))
    return flags
