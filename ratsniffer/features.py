from __future__ import annotations 
FEATURES_NAMES = ["hold_ratio", "markup", "linked_owner", "off_tree_frac", "ext_income_frac", "max_return", "linked_income", "flow_leverage", "hold_rank"]
from collections import defaultdict

def build_features(entities):
    kids = defaultdict(list)
    for e in entities.values():
        if e["parent"]:
            kids[e["parent"]].append(e["id"])
    memo = {}
    def sub_deliv(i):
        if i not in memo:
            memo[i] = entities[i]["delivered"] + sum(sub_deliv(k) for k in kids[i])
        return memo[i]
    total = sum(e["delivered"] for e in entities.values()) or 1.0
    feats = {}
    for e in entities.values():
        r = e["received"] or 1.0
        inc = e["external_income"]
        ext_amt = sum(a for _, a, _, _ in inc)
        max_ret = max((ret for _, _, ret, _ in inc if ret is not None), default=0.0)
        linked_inc = 1.0 if any(lk for _, _, _, lk in inc) else 0.0
        feats[e["id"]] = [
            (e["received"] - e["paid_out"]) / r,
            e["invoice_ratio"] - 1,
            1.0 if e["linked_owner"] else 0.0,
            sum(a for _, a in e["transfers_out"]) / r,
            ext_amt / r,
            max_ret,
            linked_inc,
            sub_deliv(e["id"]) / total,
        ]
    ids = list(feats)
    denom = max(len(ids)- 1, 1)
    for col in (0,):
        vals = {i: feats[i][col] for i in ids}
        order = sorted(ids, key=lambda i: vals[i])
        k = 0 
        while k < len(order):
            j = k 
            while j + 1 < len(order) and vals[order[j + 1]] == vals[order[k]]:
                j += 1
            avg = (k + j) / 2.0 / denom 
            for t in range(k, j + 1):
                feats[order[t]].append(avg)
            k = j + 1
    return feats 
