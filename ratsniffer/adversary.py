from __future__ import annotations
import random


def random_scheme(rng=None, max_nodes=9):
    rng = rng or random.Random()
    approp = rng.choice([1e9, 1e12, 5.9e12, 6e12])
    nodes = [dict(id="n0", name="Budget", parent=None, share=1.0,
                  capture=rng.uniform(0, 0.02), retain=rng.uniform(0, 0.03),
                  audit=rng.uniform(0.2, 0.5))]
    count = rng.randint(4, max_nodes)
    for i in range(1, count):
        parent = rng.choice(nodes)["id"]
        dirty = rng.random() < 0.5
        node = dict(id=f"n{i}", name=f"Unit {i}", parent=parent, share=rng.uniform(0.2, 1.0),
                    capture=rng.uniform(0.15, 0.5) if dirty else rng.uniform(0, 0.05),
                    retain=rng.uniform(0, 0.15),
                    audit=rng.uniform(0.02, 0.2) if dirty else rng.uniform(0.2, 0.45))
        if not dirty and rng.random() < 0.3:
            node["markup"] = rng.uniform(0.0, 0.06)
        if not dirty and rng.random() < 0.2:
            node["linkedOwner"] = "related"
        if dirty and rng.random() < 0.5:
            node["markup"] = rng.uniform(-0.5, 0.8)
        if dirty and rng.random() < 0.4:
            node["linkedOwner"] = "insider"
        if dirty and rng.random() < 0.25:
            node["phantom"] = rng.uniform(0.3, 0.8)
        if rng.random() < 0.18:
            linked = dirty and rng.random() < 0.5
            toogood = dirty and not linked and rng.random() < 0.5
            node["externalIncome"] = [{"source": "shell" if linked else "market",
                                       "amount": approp * rng.uniform(0.01, 0.05),
                                       "return": rng.uniform(0.3, 0.8) if toogood else rng.uniform(0.04, 0.2),
                                       "linked": linked}]
        nodes.append(node)
    for n in nodes[1:]:
        if n["capture"] > 0.15 and rng.random() < 0.35:
            tgt = rng.choice(nodes)
            if tgt["id"] != n["id"]:
                t = {"to": tgt["id"], "rate": rng.uniform(0.2, 0.7)}
                if rng.random() < 0.3:
                    t["chunks"] = rng.randint(6, 20)
                n.setdefault("transfers", []).append(t)
    parents = {n["parent"] for n in nodes if n.get("parent")}
    for n in nodes[1:]:
        if n["id"] not in parents:
            n["frontline"] = True
            n["retain"] = 0
    return {"appropriation": approp, "nodes": nodes}


def disguised_scheme(rng=None, n_dept=4, n_clean=30, n_dirty=3):
    rng = rng or random.Random()
    approp = rng.choice([1e12, 5.9e12, 6e12])
    nodes = [dict(id="n0", name="Budget", parent=None, share=1.0,
                  capture=rng.uniform(0, 0.01), retain=0, audit=rng.uniform(0.3, 0.5))]
    depts = []
    i = 1
    for _ in range(n_dept):
        nodes.append(dict(id=f"n{i}", name=f"Dept {i}", parent="n0", share=rng.uniform(0.5, 1.0),
                          capture=rng.uniform(0, 0.02), retain=rng.uniform(0, 0.03), audit=rng.uniform(0.3, 0.5)))
        depts.append(f"n{i}"); i += 1
    for _ in range(n_clean):
        node = dict(id=f"n{i}", name=f"Service {i}", parent=rng.choice(depts), share=rng.uniform(0.3, 1.0),
                    capture=rng.uniform(0, 0.01), retain=0, audit=rng.uniform(0.3, 0.5), frontline=True)
        if rng.random() < 0.4:
            node["externalIncome"] = [{"source": "market", "amount": approp * rng.uniform(0.01, 0.04),
                                       "return": rng.uniform(0.04, 0.15), "linked": False}]
        if rng.random() < 0.3:
            node["markup"] = rng.uniform(0.0, 0.06)
        if rng.random() < 0.2:
            node["linkedOwner"] = "related"
        nodes.append(node); i += 1
    for _ in range(n_dirty):
        node = dict(id=f"n{i}", name=f"Vendor {i}", parent=rng.choice(depts), share=rng.uniform(0.3, 1.0),
                    capture=rng.uniform(0, 0.01), retain=0, audit=rng.uniform(0.3, 0.5), frontline=True, corrupt=True)
        trick = rng.choice(["skim", "markup", "launder"])
        if trick == "skim":
            node["capture"] = rng.uniform(0.04, 0.075)
        elif trick == "markup":
            node["markup"] = rng.uniform(0.04, 0.12)
        else:
            node["externalIncome"] = [{"source": "market", "amount": approp * rng.uniform(0.02, 0.05),
                                       "return": rng.uniform(0.18, 0.248), "linked": False}]
        nodes.append(node); i += 1
    return {"appropriation": approp, "nodes": nodes}

def mutate(model, rng=None):
    rng = rng or random.Random()
    m = {"appropriation": model["appropriation"],
         "nodes": [dict(n, transfers=[dict(t) for t in n.get("transfers", [])]) for n in model["nodes"]]}
    nodes = m["nodes"]
    pool = nodes[1:] or nodes
    op = rng.random()
    if op < 0.25:
        n = rng.choice(pool)
        n["capture"] = rng.uniform(0.03, 0.078)
        n["transfers"] = []
        n.pop("linkedOwner", None)
        n["corrupt"] = True
    elif op < 0.45:
        n = rng.choice(pool)
        n["markup"] = rng.uniform(0.0, 0.14)
        n["corrupt"] = True
    elif op < 0.6:
        n = rng.choice(pool)
        n["audit"] = rng.uniform(0.3, 0.5)
        n.pop("linkedOwner", None)
    elif op < 0.75:
        nid = f"x{rng.randrange(10**9)}"
        nodes.append(dict(id=nid, name=f"Vendor {nid}", parent=rng.choice(nodes)["id"], share=rng.uniform(0.3, 1.0),
                          capture=rng.uniform(0.03, 0.078), retain=0, audit=rng.uniform(0.3, 0.5),
                          markup=rng.uniform(0.0, 0.14), frontline=True, corrupt=True))
    elif op < 0.88:
        nid = f"x{rng.randrange(10**9)}"
        nodes.append(dict(id=nid, name=f"Service {nid}", parent=rng.choice(nodes)["id"], share=rng.uniform(0.3, 1.0),
                          capture=rng.uniform(0, 0.01), retain=0, audit=rng.uniform(0.3, 0.5), frontline=True))
    else:
        rng.choice(pool)["capture"] = rng.uniform(0, 0.5)
    for n in nodes:
        if not n.get("transfers"):
            n.pop("transfers", None)
    return m

def cascade_scheme(rng=None, depth=6, fanout=1):
    rng = rng or random.Random()
    approp = rng.choice([1e12, 5.9e12, 6e12])
    nodes = [dict(id="n0", name="Budget", parent=None, share=1.0,
                  capture=rng.uniform(0, 0.01), retain=0, audit=rng.uniform(0.3, 0.5))]
    i = 1
    spine = "n0"
    for d in range(depth):
        nid = f"n{i}"; i += 1
        dirty = rng.random() < 0.5
        nodes.append(dict(id=nid, name=f"Tier {d+1}", parent=spine, share=5.0,
                          capture=rng.uniform(0.015, 0.03) if dirty else rng.uniform(0, 0.005),
                          retain=0, audit=rng.uniform(0.3, 0.5), corrupt=dirty))
        for _ in range(fanout):
            nodes.append(dict(id=f"n{i}", name=f"Service {i}", parent=nid, share=rng.uniform(0.3, 1.0),
                              capture=rng.uniform(0, 0.01), retain=0,
                              audit=rng.uniform(0.3, 0.5), frontline=True))
            i += 1
        spine = nid
    nodes.append(dict(id=f"n{i}", name="Endpoint", parent=spine, share=1.0,
                      capture=rng.uniform(0, 0.01), retain=0, audit=rng.uniform(0.3, 0.5), frontline=True))
    return {"appropriation": approp, "nodes": nodes}