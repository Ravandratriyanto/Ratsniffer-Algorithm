from __future__ import annotations
import random


def clone(model):
    return {"appropriation": model["appropriation"],
            "nodes": [dict(n, transfers=[dict(t) for t in n.get("transfers", [])]) for n in model["nodes"]]}


def _reid(model, prefix):
    m = clone(model)
    for n in m["nodes"]:
        n["id"] = prefix + n["id"]
        if n["parent"] is not None:
            n["parent"] = prefix + n["parent"]
        for t in n.get("transfers", []):
            t["to"] = prefix + t["to"]
    return m


def crossover(a, b, rng=None):
    rng = rng or random.Random()
    child = clone(a)
    donor = _reid(b, f"x{rng.randint(0, 99999)}_")
    kids = {}
    for n in donor["nodes"]:
        kids.setdefault(n["parent"], []).append(n["id"])
    nonroot = [n for n in donor["nodes"] if n["parent"] is not None]
    if not nonroot:
        return child
    sub_root = rng.choice(nonroot)
    keep, stack = set(), [sub_root["id"]]
    while stack:
        x = stack.pop()
        keep.add(x)
        stack += kids.get(x, [])
    graft = [dict(n) for n in donor["nodes"] if n["id"] in keep]
    host = rng.choice(child["nodes"])["id"]
    for n in graft:
        if n["id"] == sub_root["id"]:
            n["parent"] = host
    all_nodes = child["nodes"] + graft
    ids = {n["id"] for n in all_nodes}
    for n in all_nodes:
        if n.get("transfers"):
            n["transfers"] = [t for t in n["transfers"] if t["to"] in ids]
            if not n["transfers"]:
                del n["transfers"]
    child["nodes"] = all_nodes
    return child


def inject_motif(model, rng=None):
    rng = rng or random.Random()
    m = clone(model)
    motif = rng.choice(["skim", "markup", "kickback", "shell", "ghost", "nominee","under_invoice", "phantom", "structuring", "laundered_income"])
    n = rng.choice(m["nodes"][1:] or m["nodes"])
    if motif == "skim":
        n["capture"] = rng.uniform(0.2, 0.5); n["audit"] = rng.uniform(0.02, 0.15)
    elif motif == "markup":
        n["markup"] = rng.uniform(0.3, 0.8)
    elif motif == "kickback":
        tgt = rng.choice(m["nodes"])
        if tgt["id"] != n["id"]:
            n.setdefault("transfers", []).append({"to": tgt["id"], "rate": rng.uniform(0.3, 0.7)})
    elif motif == "shell" and n["parent"]:
        sid = f"shell{rng.randint(0, 99999)}"
        m["nodes"].append(dict(id=sid, name="Shell", parent=n["parent"], share=1.0,
                               capture=rng.uniform(0.1, 0.3), retain=0.05, audit=0.08, markup=rng.uniform(0.3, 0.6)))
        n["parent"] = sid
    elif motif == "ghost":
        n["frontline"] = True; n["ghost"] = True; n.pop("transfers", None)
    elif motif == "nominee":
        n["linkedOwner"] = "nominee"
    elif motif == "under_invoice":
        n["markup"] = rng.uniform(-0.6, -0.2)
    elif motif == "phantom":
        n["phantom"] = rng.uniform(0.3, 0.8)
    elif motif == "structuring":
        if n.get("transfers"):
            n["transfers"][0]["chunks"] = rng.randint(6, 20)
        else:
            tgt = rng.choice(m["nodes"])
            if tgt["id"] != n["id"]:
                n.setdefault("transfers", []).append({"to": tgt["id"], "rate": rng.uniform(0.3, 0.7), "chunks": rng.randint(6, 20)})
    elif motif == "laundered_income":
        n["externalIncome"] = [{"source": "shell", "amount": model["appropriation"] * 0.03, "return": 0.08, "linked": True}]
    return m


def breed(pop, rng=None, n=20):
    rng = rng or random.Random()
    out = []
    for _ in range(n):
        if len(pop) >= 2 and rng.random() < 0.6:
            a, b = rng.sample(pop, 2)
            out.append(crossover(a, b, rng))
        else:
            out.append(inject_motif(rng.choice(pop), rng))
    return out
