from __future__ import annotations 
from dataclasses import dataclass 

@dataclass
class Flag:
    entity: str
    detector: str
    severity: float   
    detail: str
PRICE_BAND_HI = 1.15  
PRICE_BAND_LO = 0.85
STRUCT_THRESHOLD = 1e7
STRUCT_MIN_CHUNKS = 5


def price_band(e):
    r = e["invoice_ratio"]
    if r > PRICE_BAND_HI:
        return Flag(e["id"], "price_band", min(1.0, (r - PRICE_BAND_HI) / PRICE_BAND_HI),
                    f"invoice {(r - 1) * 100:.0f}% over fair price")
    if r < PRICE_BAND_LO:
        return Flag(e["id"], "under_invoice", min(1.0, (PRICE_BAND_LO - r) / PRICE_BAND_LO),
                    f"invoice {(1 - r) * 100:.0f}% under fair price")
    return None


def self_deal(e):
    r = e["received"]
    hold = (r - e["paid_out"]) / r if r else 0
    if e["linked_owner"] and hold > 0.2:
        return Flag(e["id"], "self_deal", 0.6,
                    f"related party {e['linked_owner']} keeping {hold * 100:.0f}% of inflow")
    return None


def off_tree_transfer(e):
    if e["transfers_out"]:
        total = sum(a for _, a in e["transfers_out"])
        frac = total / e["received"] if e["received"] else 0
        tgt = ", ".join(to for to, _ in e["transfers_out"])
        return Flag(e["id"], "off_tree_transfer", min(1.0, frac * 3),
                    f"routes {frac * 100:.0f}% of inflow off-tree to {tgt}")
    return None

def structuring(e):
    for amt, ch in e.get("tx_chunks", []):
        if ch >= STRUCT_MIN_CHUNKS and amt / ch < STRUCT_THRESHOLD:
            return Flag(e["id"], "structuring", min(1.0, ch / 20), f"split a transfer into {ch} sub-threshold chunks")
        return None

GATES = [price_band, self_deal, off_tree_transfer, structuring]


def run_gates(entities) -> list[Flag]:
    flags = []
    for e in entities.values():
        for g in GATES:
            f = g(e)
            if f:
                flags.append(f)
    return flags
