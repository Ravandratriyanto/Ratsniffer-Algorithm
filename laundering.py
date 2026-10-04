from __future__ import annotations 
import networkx as nx 
from gates import Flag 

def round_trip(entities):
    G = nx.DiGraph()
    for e in entities.values():
        if e["parent"]:
            G.add_edge(e["parent"], e["id"])
        for to, amt in e["transfers_out"]:
            G.add_edge(e["id"], to)
    flags, seen = [], set()
    for cyc in nx.simple_cycles(G):
        if len(cyc) < 2:
            continue
        for nid in cyc:
            if nid in entities and nid not in seen:
                seen.add(nid)
                flags.append(Flag(nid, "round_trip", 0.8,
                    f"funds cycle back to source through {len(cyc)} hops"))
    return flags

def layering(entities, pass_ratio=0.92, min_chain=3):
    kids = {}
    for e in entities.values():
        if e["parent"]:
            kids.setdefault(e["parent"], []).append(e["id"])
    def is_conduit(e):
        r = e["received"] or 1.0
        return (e["parent"] and e["paid_out"] / r > pass_ratio and len(kids.get(e["id"], [])) == 1)
    chains = {}
    for e in entities.values():
        if not is_conduit(e):
            continue 
        run, cur = [], e["id"]
        while cur in entities and is_conduit(entities[curl]):
            run.append(cur)
            ch = kids.get(cur, [])
            cur = ch[0] if ch else None 
        if len(run) >= min_chain:
            for nid in run:
                chains[nid] = len(run)
    return [Flag(nid, "layering", min(1.0, depth / 5),f"pass-through conduit in a {depth}-hop layering chain")for nid, depth in chains.items()]
def run_laundering(entities):
    return round_trip(entities) + layering(entities)
