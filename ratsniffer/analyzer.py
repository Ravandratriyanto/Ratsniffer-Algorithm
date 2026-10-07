from __future__ import annotations
import statistics
from gates import Flag, PRICE_BAND_HI

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

def _children(entities):
    ch = {}
    for e in entities.values():
        if e["parent"]:
            ch.setdefault(e["parent"], []).append(e["id"])
    return ch

def markup_cluster(entities, min_cluster=2):
    ch = _children(entities)
    flags = []
    for pid, cids in ch.items():
        band = [c for c in cids if 1.0 < entities[c]["invoice_ratio"] < PRICE_BAND_HI]
        if len(band) < min_cluster:
            continue
        avg = sum(entities[c]["invoice_ratio"] for c in band) / len(band)
        flags.append(Flag(pid, "markup_cluster", min(1.0, (avg - 1) / 0.15 * len(band) / 3), f"{len(band)} children padding invoices under the alarm (avg {(avg - 1) * 100:.0f}%)"))
        for c in band:
            r = entities[c]["invoice_ratio"]
            flags.append(Flag(c, "markup_cluster", min(1.0, (r - 1) / 0.15), f"invoice {(r - 1) * 100:.0f}% over fair — sub-band but part of a cluster"))
    return flags


def holdratio_cluster(entities, floor=0.02, min_cluster=2):
    ch = _children(entities)
    flags = []
    for pid, cids in ch.items():
        band = []
        for c in cids:
            e = entities[c]
            r = e["received"]
            if r and (r - e["paid_out"]) / r > floor:
                band.append(c)
        if len(band) < min_cluster:
            continue
        for c in band:
            e = entities[c]
            h = (e["received"] - e["paid_out"]) / e["received"]
            flags.append(Flag(c, "holdratio_cluster", min(1.0, h / 0.15),
                              f"under-delivers {h * 100:.0f}% — sub-threshold but part of a cluster"))
    return flags
def subtree_leakage(entities, node_lo=0.005, node_hi=0.15, min_depth=3):
    ch = _children(entities)
    par = {c: p for p in ch for c in ch[p]}
    def skims(i):
        e = entities[i]; r = e["received"]
        return bool(r) and i in ch and node_lo < (r - e["paid_out"]) / r < node_hi
    S = {i for i in entities if skims(i)}
    down = {}
    def chain_down(i):
        if i not in down:
            down[i] = 1 + max((chain_down(c) for c in ch.get(i, []) if c in S), default=0)
        return down[i]
    def chain_up(i):
        p = par.get(i)
        return 1 + chain_up(p) if p in S else 1
    flags = []
    for i in S:
        if chain_up(i) + chain_down(i) - 1 >= min_depth:
            e = entities[i]; r = e["received"]; k = (r - e["paid_out"]) / r
            flags.append(Flag(i, "subtree_leakage", min(1.0, chain_down(i) / 6),
                              f"skims {k * 100:.1f}% inside a chain of >={min_depth} consecutive leaking tiers"))
    return flags

def run_analyzer(entities):
    return retention_anomaly(entities) + subtree_leakage(entities)
    
