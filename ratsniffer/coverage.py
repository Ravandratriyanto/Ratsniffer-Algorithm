import random
import numpy as np
from sklearn.preprocessing import StandardScaler
from sklearn.linear_model import LogisticRegression
from world import make_run
from ingest import entities_and_truth
from features import build_features
from gates import run_gates
from analyzer import run_analyzer
from laundering import run_laundering
from oracle import attest, reconcile, wealth_reconciliation
from eval import dataset, honest_dataset
from schemes import seed_bank, LIBRARY
from breed import breed
from adversary import disguised_scheme

LAYERS = ["rules", "ML", "oracle", "combined"]


def base_world(rng, dirty_fn, n_clean=10, n_dirty=3):
    ap = rng.choice([1e12, 5.9e12, 6e12])
    nodes = [dict(id="n0", name="Budget", parent=None, share=1.0, capture=rng.uniform(0, 0.01), retain=0, audit=rng.uniform(0.3, 0.5)),
             dict(id="ag", name="Agency", parent="n0", share=1.0, capture=rng.uniform(0, 0.02), retain=rng.uniform(0, 0.03), audit=rng.uniform(0.3, 0.5))]
    for i in range(n_clean):
        nodes.append(dict(id=f"s{i}", name=f"Svc{i}", parent="ag", share=rng.uniform(0.3, 1.0), capture=rng.uniform(0, 0.01), retain=0, audit=rng.uniform(0.3, 0.5), frontline=True))
    for i in range(n_dirty):
        n = dict(id=f"d{i}", name=f"Dirty{i}", parent="ag", share=rng.uniform(0.3, 1.0), capture=rng.uniform(0, 0.01), retain=0, audit=rng.uniform(0.3, 0.5), frontline=True, corrupt=True)
        dirty_fn(n, rng, ap); nodes.append(n)
    return {"appropriation": ap, "nodes": nodes}


def m_retention(n, r, a): n["capture"] = r.uniform(0.15, 0.35); n["audit"] = r.uniform(0.02, 0.15)
def m_markup(n, r, a):    n["markup"] = r.uniform(0.3, 0.6)
def m_selfdeal(n, r, a):  n["capture"] = r.uniform(0.15, 0.3); n["linkedOwner"] = "insider"; n["audit"] = r.uniform(0.02, 0.15)
def m_phantom(n, r, a):   n["phantom"] = r.uniform(0.3, 0.6)
def m_extinc(n, r, a):    n["externalIncome"] = [{"source": "shell", "amount": a * r.uniform(0.02, 0.05), "return": r.uniform(0.3, 0.6), "linked": True}]


def ring_world(rng, n_clean=10, ring=3):
    ap = rng.choice([1e12, 5.9e12, 6e12])
    nodes = [dict(id="n0", name="Budget", parent=None, share=1.0, capture=rng.uniform(0, 0.01), retain=0, audit=rng.uniform(0.3, 0.5)),
             dict(id="ag", name="Agency", parent="n0", share=1.0, capture=rng.uniform(0, 0.02), retain=rng.uniform(0, 0.03), audit=rng.uniform(0.3, 0.5))]
    for i in range(n_clean):
        nodes.append(dict(id=f"s{i}", name=f"Svc{i}", parent="ag", share=rng.uniform(0.3, 1.0), capture=rng.uniform(0, 0.01), retain=0, audit=rng.uniform(0.3, 0.5), frontline=True))
    sh = [f"sh{i}" for i in range(ring)]
    for i, sid in enumerate(sh):
        nodes.append(dict(id=sid, name=f"Shell{i}", parent="ag", share=rng.uniform(0.4, 0.9), capture=rng.uniform(0.12, 0.22), retain=0, audit=rng.uniform(0.02, 0.15), corrupt=True, frontline=True, transfers=[{"to": sh[(i + 1) % ring], "rate": rng.uniform(0.4, 0.7)}]))
    return {"appropriation": ap, "nodes": nodes}


MECH = {"retention (skim)": lambda r: base_world(r, m_retention), "markup": lambda r: base_world(r, m_markup),
        "self-deal": lambda r: base_world(r, m_selfdeal), "phantom goods": lambda r: base_world(r, m_phantom),
        "external income": lambda r: base_world(r, m_extinc), "pass-through ring": ring_world,
        "disguised cluster": disguised_scheme}


def train_ml():
    X, y, w, f = dataset(20, seed=0)
    Xh = honest_dataset(20, seed=1)
    Xtr = np.vstack([X, Xh]); ytr = np.concatenate([y, np.zeros(len(Xh))])
    sc = StandardScaler().fit(Xtr)
    clf = LogisticRegression(max_iter=1000, class_weight="balanced").fit(sc.transform(Xtr), ytr)
    tau = float(np.quantile(clf.predict_proba(sc.transform(honest_dataset(20, seed=2)))[:, 1], 0.90))
    return sc, clf, tau


def layer_flags(run, ent, sc, clf, tau):
    rules = {fl.entity for fl in run_gates(ent) + run_analyzer(ent) + run_laundering(ent)}
    oracle = {fl.entity for fl in reconcile(run, attest(run, coverage=1.0))} | {fl.entity for fl in wealth_reconciliation(ent)}
    ids = list(ent); ft = build_features(ent)
    p = clf.predict_proba(sc.transform([ft[i] for i in ids]))[:, 1]
    ml = {i for i, pp in zip(ids, p) if pp >= tau}
    return {"rules": rules, "ML": ml, "oracle": oracle, "combined": rules | ml | oracle}


def recall_fpr(models, sc, clf, tau):
    rec = {k: [0, 0] for k in LAYERS}; fp = {k: [0, 0] for k in LAYERS}
    for mdl in models:
        try:
            run = make_run(mdl)
        except Exception:
            continue
        ent, truth = entities_and_truth(run)
        cor = {i for i in ent if truth[i]["label"] == "corrupt"}
        cln = {i for i in ent if truth[i]["label"] != "corrupt"}
        flags = layer_flags(run, ent, sc, clf, tau)
        for k, fl in flags.items():
            rec[k][0] += len(cor & fl); rec[k][1] += len(cor)
            fp[k][0] += len(cln & fl); fp[k][1] += len(cln)
    R = lambda d, k: d[k][0] / d[k][1] if d[k][1] else 0.0
    return {k: R(rec, k) for k in LAYERS}, {k: R(fp, k) for k in LAYERS}, rec["rules"][1]


def row(name, rec, nc=None):
    tail = f"{nc:>9}" if nc is not None else ""
    print(f"{name:<18}" + "".join(f"{rec[k]:>9.0%}" for k in LAYERS) + tail)


def main():
    sc, clf, tau = train_ml()
    print(f"ML threshold calibrated to 10% false alarms on honest worlds (tau={tau:.2f})\n")
    print("COVERAGE MATRIX — recall of corrupt nodes, synthetic single-mechanism worlds")
    print(f"{'mechanism':<18}" + "".join(f"{k:>9}" for k in LAYERS))
    rng = random.Random(42)
    for name, gen in MECH.items():
        rec, _, _ = recall_fpr([gen(rng) for _ in range(12)], sc, clf, tau)
        row(name, rec)

    print("\nREAL-CASE seeds (replayed) + BRED variants — recall  (ML never trained on these)")
    print(f"{'scheme':<18}" + "".join(f"{k:>9}" for k in LAYERS) + f"{'#corrupt':>9}")
    for nm, fn in zip(["ektp", "launder", "ghost", "kickback", "embezzle"], LIBRARY):
        rec, _, nc = recall_fpr([fn()], sc, clf, tau)
        row(nm, rec, nc)
    bred = breed(seed_bank(), random.Random(7), n=40)
    rec, fp, nc = recall_fpr(bred, sc, clf, tau)
    row("bred (x40)", rec, nc)
    print(f"\nbred-world FALSE-ALARM rate (clean nodes flagged):")
    print(f"{'':<18}" + "".join(f"{fp[k]:>9.0%}" for k in LAYERS))


if __name__ == "__main__":
    main()
