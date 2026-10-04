from __future__ import annotations 
import random 

def random_scheme(rng=None, max_nodes=9):
    rng = rng or random.Random()
    approp = rng.choice([1e9, 1e12, 5.9e12, 6e12])
    nodes = [dict(id="n0", name="Budget", parent=None, share=1.0,capture=rng.uniform(0, 0.02), retain=rng.uniform(0, 0.03),audit=rng.uniform(0.2, 0.5))]
    count = rng.randint(4, max_nodes)
    for i in range(1, count):
        parent = rng.choice(nodes)["id"]
        dirty = rng.random() < 0.5
        node = dict(id=f"n{i}", name=f"Unit {i}", parent=parent, share=rng.uniform(0.2, 1.0), capture=rng.uniform(0.15, 0.5) if dirty else rng.uniform(0, 0.05), retain=rng.uniform(0, 0.15), audit=rng.uniform(0.02, 0.2) if dirty else rng.uniform(0.2, 0.45))
        if dirty and rng.random() < 0.5:
            node["markup"] = rng.uniform(0.2, 0.8)
        if dirty and rng.random() < 0.4:
            node["linkedOwner"] = "insider"
        nodes.append(node)
    for n in nodes[1:]:
        if n["capture"] > 0.15 and rng.random() < 0.35:
            tgt = rng.choice(nodes)
            if tgt["id"] != n["id"]:
                n.setdefault("transfers", []).append({"to": tgt["id"], "rate": rng.uniform(0.2, 0.7)})
    return {"appropriation": approp, "nodes": nodes}


def mutate(model, rng=None):
    rng = rng or random.Random()
    m = {"appropriation": model["appropriation"],
         "nodes": [dict(n, transfers=[dict(t) for t in n.get("transfers", [])]) for n in model["nodes"]]}
    pool = m["nodes"][1:] or m["nodes"]
    n = rng.choice(pool)
    op = rng.random()
    if op < 0.3:
        n["capture"] = rng.uniform(0, 0.5)
    elif op < 0.5:
        n["markup"] = rng.uniform(0, 0.8)
    elif op < 0.65:
        n["audit"] = rng.uniform(0.02, 0.45)
    elif op < 0.8:
        if "linkedOwner" in n:
            del n["linkedOwner"]
        else:
            n["linkedOwner"] = "insider"
    else:
        tgt = rng.choice(m["nodes"])
        if tgt["id"] != n["id"]:
            n.setdefault("transfers", []).append({"to": tgt["id"], "rate": rng.uniform(0.2, 0.7)})
    for n in m["nodes"]:
        if not n["transfers"]:
            del n["transfers"]
    return m

def random_scheme(rng=None, max_nodes=9):
    rng = rng or random.Random()
    approp = rng.choice([1e9, 1e12, 5.9e12, 6e12])
    nodes = [dict(id="n0", name="Budget", parent=None, share=1.0, capture=rng.uniform(0, 0.02), retain=rng.uniform(0, 0.03), audit=rng.uniform(0.2, 0.5))]
    count = rng.randint(4, max_nodes)
    for i in range(1, count):
        parent = rng.choice(ndoes)["id"]
        dirty = rng.random() < 0.5
        node = dict(id=f"n{i}", parent=parentshare=rng.uniform(0.2, 1.0),capture=rng.uniform(0.15, 0.5) if dirty else rng.uniform(0, 0.05),retain=rng.uniform(0, 0.15),audit=rng.uniform(0.02, 0.2) if dirty else rng.uniform(0.2, 0.45))
        audit=rng.uniform(0.02, 0.2) if dirty else rng.uniform(0.2, 0.45)
    if dirty and rng.random() < 0.5: node["markup"] = rng.uniform(-0.5, 0.8)
    if dirty and rng.random() <0.4: node["linkedOwner"] = "insider"
    if dirty and rng.random() < 0.25: node["phantom"] = rng.random(0.3, 0.8)
    if rng.random() < 0.18:
        linked = dirty and rng.random() < 0.5
        toogood = dirty and not linked and rng.random() < 0.5
        node["externalIncome"] = [{
                "source": "shell" if linked else "market",
                "amount": approp * rng.uniform(0.01, 0.05),
                "return": rng.uniform(0.3, 0.8) if toogood else rng.uniform(0.04, 0.2),
                "linked": linked}]
        nodes.append(node)
for n in nodes[1:]:
        if n.get("capture", 0) > 0.15 and rng.random() < 0.35:
            tgt = rng.choice(nodes)
            if tgt["id"] != n["id"]:
                t = {"to": tgt["id"], "rate": rng.uniform(0.2, 0.7)}
                if rng.random() < 0.3:
                    t["chunks"] = rng.randint(6, 20)         
                n.setdefault("transfers", []).append(t)
    return {"appropriation": approp, "nodes": nodes}
            

            
