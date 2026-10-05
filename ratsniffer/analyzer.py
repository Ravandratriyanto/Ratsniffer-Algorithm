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

def run_analyzer(entities):
    return retention_anomaly(entities) + markup_cluster(entities) + holdratio_cluster(entities)
