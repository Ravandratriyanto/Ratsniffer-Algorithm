from __future__ import annotations


def _clamp(v, a, b):
    return max(a, min(b, v))


def _rates(n, clean):
    if clean:
        return 0.0, _clamp(n.get("retain", 0), 0, 1)
    skim = n.get("capture", 0)
    m = n.get("markup", 0)
    infl = m / (1 + m)
    raw = skim + infl - skim * infl
    c = _clamp(raw * (1 - n.get("audit", 0)), 0, 1)
    r = _clamp(n.get("retain", 0), 0, 1 - c)
    return c, r


def simulate(model, clean=False):
    nodes = {n["id"]: n for n in model["nodes"]}
    kids = {n["id"]: [] for n in model["nodes"]}
    root = None
    for n in model["nodes"]:
        if n.get("parent") is None:
            root = n
        else:
            kids[n["parent"]].append(n)

    S = {}
    appropriation = model["appropriation"]

    def outflows(n):
        return [t for t in n.get("transfers", []) if t.get("rate", 0) > 0 and t["to"] in nodes]

    def share_total(ch):
        return sum(k["share"] for k in ch) or 1

    def base(n, received):
        c, r = _rates(n, clean)
        ch = kids[n["id"]]
        diverted = received * c
        retained = down = delivered = true_d = 0.0
        if n.get("frontline"):
            delivered = received - diverted
            true_d = delivered * 0.05 if (not clean and n.get("ghost")) else delivered
        elif not ch:
            retained = received - diverted
        else:
            retained = received * r
            down = received - diverted - retained
        S[n["id"]] = dict(received=received, diverted=diverted, retained=retained, down=down,
                          delivered=delivered, trueDelivered=true_d, kickedOut=0.0,
                          fromParent=received, fromKickback=0.0, fromKickbackDirect=0.0)
        tot = share_total(ch)
        for k in ch:
            base(k, down * k["share"] / tot)

    def inject(node_id, amount, depth):
        n = nodes.get(node_id)
        if not n or depth > 8 or amount < appropriation * 1e-9:
            return 0.0
        c, r = _rates(n, clean)
        ch = kids[node_id]
        diverted = amount * c
        retained = down = delivered = true_d = 0.0
        if n.get("frontline"):
            delivered = amount - diverted
            true_d = delivered * 0.05 if (not clean and n.get("ghost")) else delivered
        elif not ch:
            retained = amount - diverted
        else:
            retained = amount * r
            down = amount - diverted - retained
        s = S[node_id]
        s["received"] += amount; s["diverted"] += diverted; s["retained"] += retained
        s["down"] += down; s["delivered"] += delivered; s["trueDelivered"] += true_d
        s["fromKickback"] += amount
        tot = share_total(ch)
        passed = 0.0
        for k in ch:
            passed += inject(k["id"], down * k["share"] / tot, depth + 1)
        stuck = down - passed
        if stuck > 0:
            s["retained"] += stuck; s["down"] -= stuck
        if not clean:
            for t in outflows(n):
                seed = min(diverted * t["rate"], max(0, s["diverted"]))
                if seed <= 0:
                    continue
                out = inject(t["to"], seed, depth + 1)
                s["diverted"] -= out; s["kickedOut"] += out
                S[t["to"]]["fromKickbackDirect"] += out
        return amount

    base(root, appropriation)
    if not clean:
        seeds = [(n, t["to"], S[n["id"]]["diverted"] * t["rate"])
                 for n in model["nodes"] for t in outflows(n)]
        for n, to, amount in seeds:
            s = S[n["id"]]
            seed = min(amount, max(0, s["diverted"]))
            if seed <= 0:
                continue
            out = inject(to, seed, 1)
            s["diverted"] -= out; s["kickedOut"] += out
            S[to]["fromKickbackDirect"] += out
    return S


def make_run(model):
    S = simulate(model, clean=False)
    out = []
    for n in model["nodes"]:
        c, _ = _rates(n, False)
        schemes = []
        if [t for t in n.get("transfers", []) if t.get("rate", 0) > 0]:
            schemes.append("kickback_loop")
        if n.get("ghost"):
            schemes.append("ghost_recipient")
        if n.get("markup", 0) > 0:
            schemes.append("invoice_inflation")
        row = dict(n)
        row.update(S[n["id"]])
        row["effectiveCapture"] = c
        row["schemes"] = schemes
        row["effectiveCapture"] = c
        row["schemes"] = schemes
        inc = n.get("externalIncome", [])
        dirty_income = any(t.get("linked") or (t.get("return") is not None and t["return"] > 0.25) for t in inc)
        mk = n.get("markup", 0)
        extra = mk < -0.1 or n.get("phantom", 0) > 0.05 or any(t.get("chunks", 1) >= 5 for t in n.get("transfers", []))
        row["label"] = "corrupt" if (n.get("corrupt") or schemes or c > 0.08 or dirty_income or extra) else "clean"
        out.append(row)
    return {"appropriation": model["appropriation"], "nodes": out}
