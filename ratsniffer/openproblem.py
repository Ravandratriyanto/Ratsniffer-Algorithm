import random
import numpy as np
from world import make_run
from ingest import entities_and_truth
from features import build_features, FEATURES_NAMES
from eval import fit_score
from adversary import random_scheme, disguised_scheme, cascade_scheme
from schemes import seed_bank
from breed import breed

HR = FEATURES_NAMES.index("hold_rank")
HOLD_FUNCS = ["ministry", "water"]          # functions that legitimately hold reserves
DELIVER_FUNCS = ["school", "hospital", "roads"]
ALLF = HOLD_FUNCS + DELIVER_FUNCS

def realistic_honest(rng, p_hold, n_dept=4, n_svc=30):
    ap = rng.choice([1e12, 5.9e12, 6e12])
    nodes = [dict(id="n0", name="B", parent=None, share=1, capture=rng.uniform(0, .01), retain=0, audit=rng.uniform(.3, .5))]
    depts = []
    for d in range(n_dept):
        did = f"d{d}"
        nodes.append(dict(id=did, name=did, parent="n0", share=rng.uniform(.5, 1), capture=rng.uniform(0, .02), retain=rng.uniform(0, .03), audit=rng.uniform(.3, .5), function=rng.choice(ALLF)))
        depts.append(did)
    for s in range(n_svc):
        holds = rng.random() < p_hold
        func = rng.choice(HOLD_FUNCS) if holds else rng.choice(DELIVER_FUNCS)
        n = dict(id=f"s{s}", name=f"s{s}", parent=rng.choice(depts), share=rng.uniform(.3, 1), capture=rng.uniform(0, .01), audit=rng.uniform(.3, .5), function=func)
        if holds:
            n["retain"] = rng.uniform(.15, .40)
        else:
            n["frontline"] = True; n["retain"] = 0
        nodes.append(n)
    return {"appropriation": ap, "nodes": nodes}

def build(models, fseed=0):
    fr = random.Random(fseed); X = []; y = []; fn = []
    for mdl in models:
        try:
            run = make_run(mdl)
        except Exception:
            continue
        fm = {n["id"]: (n.get("function") or fr.choice(ALLF)) for n in run["nodes"]}
        ent, truth = entities_and_truth(run); ft = build_features(ent)
        for i in ent:
            X.append(ft[i]); y.append(1 if truth[i]["label"] == "corrupt" else 0); fn.append(fm[i])
    return np.array(X, float), np.array(y), np.array(fn)

def ranks01(v):
    o = np.argsort(v, kind="mergesort"); r = np.empty(len(v)); sv = v[o]; i = 0
    while i < len(sv):
        j = i
        while j + 1 < len(sv) and sv[j + 1] == sv[i]:
            j += 1
        r[o[i:j + 1]] = (i + j) / 2.0; i = j + 1
    return r / max(len(v) - 1, 1)

def regroup(X, fn):
    X2 = X.copy()
    for g in np.unique(fn):
        idx = np.where(fn == g)[0]; X2[idx, HR] = ranks01(X[idx, 0])
    return X2

def train_pool(n, seed):
    rng = random.Random(seed); ms = []
    for g in (random_scheme, disguised_scheme, cascade_scheme):
        for _ in range(n): ms.append(g(rng))
    return ms

Xs, ys, fns = build(train_pool(20, 0))
Xho, yho, fnho = build([realistic_honest(random.Random(100 + i), 0.0) for i in range(20)])
Xtr = np.vstack([Xs, Xho]); ytr = np.concatenate([ys, np.zeros(len(Xho))]); fntr = np.concatenate([fns, fnho])
Xbr, ybr, fnbr = build(breed(seed_bank(), random.Random(7), n=40))

def variant(regr):
    Xt = regroup(Xtr, fntr) if regr else Xtr
    Xc, _, fnc = build([realistic_honest(random.Random(500 + i), 0.0) for i in range(20)])
    if regr: Xc = regroup(Xc, fnc)
    tau = float(np.quantile(fit_score(Xt, ytr, Xc), 0.90))
    curve = []
    for ph in (0.0, 0.1, 0.2, 0.3, 0.5):
        Xh, _, fh = build([realistic_honest(random.Random(600 + int(ph * 100) + i), ph) for i in range(20)])
        if regr: Xh = regroup(Xh, fh)
        curve.append((ph, (fit_score(Xt, ytr, Xh) >= tau).mean()))
    Xb = regroup(Xbr, fnbr) if regr else Xbr
    sb = fit_score(Xt, ytr, Xb)
    return tau, curve, (sb[ybr == 1] >= tau).mean(), sb

print("=== Exp 1+2: honest FPR vs holding share, global vs function-grouped hold_rank ===")
for label, regr in [("global  hold_rank", False), ("function hold_rank", True)]:
    tau, curve, br, sb = variant(regr)
    print(f"\n[{label}]  bred recall@(10%-honest-FPR) = {br:.2f}")
    print("   " + "  ".join(f"p_hold={ph:.1f}:{fpr:5.1%}" for ph, fpr in curve))

print("\n=== Exp 3: oracle with a budget (function variant) — ML ranks, oracle confirms ===")
tau, curve, br, sb = variant(True)
Xh, yh, fh = build([realistic_honest(random.Random(700 + i), 0.3) for i in range(20)])
sh = fit_score(regroup(Xtr, fntr), ytr, regroup(Xh, fh))
scores = np.concatenate([sb, sh]); labels = np.concatenate([ybr, yh])
order = np.argsort(-scores)
print(f"   mixed pool: {len(labels)} offices, {int(labels.sum())} corrupt ({labels.mean():.1%})")
for k in (0.01, 0.05, 0.10):
    top = order[:max(1, int(k * len(order)))]
    print(f"   k={k:.0%}  precision@k {labels[top].mean():.2f}   recall@k {labels[top].sum()/labels.sum():.2f}")
