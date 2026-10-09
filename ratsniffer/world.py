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
    events = []
    appropriation = model["appropriation"]

    def ev(src, dst, amount, kind, depth, t=None):
        # One entry per movement of money. inject() returns 0.0 when it bounces a
        # call (depth cap, or dust), so a zero amount means nothing actually moved.
        if amount <= 0:
            return
        e = {"seq": len(events), "from": src, "to": dst,
             "amount": amount, "kind": kind, "depth": depth}
        if t is not None:
            e["rate"] = t.get("rate")
            if t.get("chunks"):
                e["chunks"] = t["chunks"]
        events.append(e)

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
            amt = down * k["share"] / tot
            ev(n["id"], k["id"], amt, "funding", 0)
            base(k, amt)

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
            amt = down * k["share"] / tot
            got = inject(k["id"], amt, depth + 1)
            ev(node_id, k["id"], got, "funding", depth + 1)
            passed += got
        stuck = down - passed
        if stuck > 0:
            s["retained"] += stuck; s["down"] -= stuck
        if not clean:
            for t in outflows(n):
                seed = min(diverted * t["rate"], max(0, s["diverted"]))
                if seed <= 0:
                    continue
                out = inject(t["to"], seed, depth + 1)
                ev(node_id, t["to"], out, "transfer", depth + 1, t)
                s["diverted"] -= out; s["kickedOut"] += out
                S[t["to"]]["fromKickbackDirect"] += out
        return amount

    ev(None, root["id"], appropriation, "appropriation", 0)
    base(root, appropriation)
    if not clean:
        seeds = [(n, t, S[n["id"]]["diverted"] * t["rate"])
                 for n in model["nodes"] for t in outflows(n)]
        for n, t, amount in seeds:
            s = S[n["id"]]
            seed = min(amount, max(0, s["diverted"]))
            if seed <= 0:
                continue
            out = inject(t["to"], seed, 1)
            ev(n["id"], t["to"], out, "transfer", 1, t)
            s["diverted"] -= out; s["kickedOut"] += out
            S[t["to"]]["fromKickbackDirect"] += out
    for nid, s in S.items():
        s["cashedOut"] = s["delivered"] + s["diverted"]
        ev(nid, "__bank", s["cashedOut"], "cashout", 0)
    return S, events


def make_run(model):
    S, events = simulate(model, clean=False)
    out = []
    for n in model["nodes"]:
        s = S[n["id"]]
        bal = s["diverted"] + s["retained"] + s["down"] + s["delivered"] + s["kickedOut"]
        assert abs(s["received"] - bal) <= max(1.0, s["received"]) * 1e-6, f"conservation broke at {n['id']}"
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
        row["label"] = "corrupt" if (n.get("corrupt") or c > 0.08 or n.get("ghost") or n.get("phantom", 0) > 0.05) else "clean"
        out.append(row)
    return {"appropriation": model["appropriation"], "nodes": out, "events": events}

