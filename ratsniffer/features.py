from __future__ import annotations 
FEATURES_NAMES = ["hold_ratio", "markup", "linked_owner", "off_tree_frac", "is_leaf","received_share", "num_children", "ext_income_frac", "max_return", "linked_income"]

def build_features(entities):
    children = {}
    for e in entities.values():
        if e["parent"]:
            children[e["parent"]] = children.get(e["parent"], 0) + 1
    total = sum(e["received"] for e in entities.values() if e["parent"] is None) or 1.0
    feats = {}
    for e in entities.values():
        r = e["received"] or 1.0 
        nkids = children.get(e["id"], 0)
        inc = e["external_income"]
        ext_amt = sum(a for _, a, _, _ in inc)
        max_ret = max((ret for _, _, ret, _ in inc if ret is not None), default=0.0)
        linked_inc = 1.0 if any(lk for _, _, _, lk in inc) else 0.0
        feats[e["id"]] = [
            (e["received"] - e["paid_out"]) / r,
            e["invoice_ratio"] - 1, 
            1.0 if e["linked_owner"] else 0.0, 
            sum(a for _, a in e["transfers_out"]) / r,
            0.0 if nkids else 1.0,
            e["received"] / total,
            float(nkids),
            ext_amt / r, 
            max_ret, 
            linked_inc, 

        ]
    return feats 
