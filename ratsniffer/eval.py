import random
import numpy as np
from sklearn.metrics import roc_auc_score, average_precision_score, roc_curve
from sklearn.linear_model import LogisticRegression
from sklearn.preprocessing import StandardScaler
from world import make_run
from ingest import entities_and_truth
from features import build_features, FEATURES_NAMES
from adversary import random_scheme, disguised_scheme, cascade_scheme

FAMILIES = {
    "random": random_scheme,
    "disguised": disguised_scheme,
    "cascade": cascade_scheme,
}

def dataset(n_worlds, seed):
    rng = random.Random(seed)
    X, y, world, fam = [], [], [], []
    wid = 0
    for name, gen in FAMILIES.items():
        for _ in range(n_worlds):
            ent, truth = entities_and_truth(make_run(gen(rng)))
            feats = build_features(ent)
            for i in ent:
                X.append(feats[i]); y.append(1 if truth[i]["label"] == "corrupt" else 0)
                world.append(wid); fam.append(name)
            wid += 1
    return np.array(X, float), np.array(y), np.array(world), np.array(fam)

def fit_score(Xtr, ytr, Xte):
    sc = StandardScaler().fit(Xtr)
    clf = LogisticRegression(max_iter=1000, class_weight="balanced").fit(sc.transform(Xtr), ytr)
    return clf.predict_proba(sc.transform(Xte))[:, 1]

def metrics(yte, p):
    pred = p >= 0.5
    tn = int((yte == 0).sum()); fp = int(((pred == 1) & (yte == 0)).sum())
    return roc_auc_score(yte, p), average_precision_score(yte, p), (fp / tn if tn else 0.0)

def split_by_world(X, y, w, frac=0.5, seed=0):
    ids = sorted(set(w.tolist())); random.Random(seed).shuffle(ids)
    tr = set(ids[:int(len(ids) * frac)])
    m = np.array([wi in tr for wi in w])
    return X[m], y[m], X[~m], y[~m]

def ms(a):
    return f"{np.mean(a):.3f}+/-{np.std(a):.3f}  [{min(a):.3f}, {max(a):.3f}]"

def single_feature_auc(X, y):
    print("[single-feature AUC]  (near 1.0/0.0 => one feature alone separates => too easy)")
    for j, name in enumerate(FEATURES_NAMES):
        col = X[:, j]
        if len(set(col.tolist())) < 2:
            print(f"  {name:<16} constant"); continue
        auc = roc_auc_score(y, col)
        print(f"  {name:<16} AUC {auc:.3f}{'  <-- WARN' if auc > 0.95 or auc < 0.05 else ''}")

def leak_audit(X, y):
    print(f"\n[conditional leak audit]  base corrupt-rate {y.mean():.1%}  (feature active => ~100%/0% corrupt on >=10 rows = answer key)")
    for j, name in enumerate(FEATURES_NAMES):
        m = X[:, j] > 0
        n = int(m.sum())
        if n == 0:
            print(f"  {name:<16} never active"); continue
        rate = y[m].mean()
        warn = "  <-- LEAK" if n >= 10 and (rate > 0.98 or rate < 0.02) else ""
        print(f"  {name:<16} active in {n:>4} rows, corrupt-rate {rate:.1%}{warn}")
def recall_at_fpr(yte, p, target):
    fpr, tpr, _ = roc_curve(yte, p)
    ok = fpr <= target
    return tpr[ok].max() if ok.any() else 0.0

def held_out_ci(K=5, n_worlds=20):
    fam = {name: {5: [], 10: []} for name in FAMILIES}
    hon = []
    for s in range(K):
        X, y, w, f = dataset(n_worlds, seed=s)
        Xh_tr = honest_dataset(n_worlds, seed=300 + s)
        Xh_cal = honest_dataset(n_worlds, seed=100 + s)
        Xh_tst = honest_dataset(n_worlds, seed=200 + s)
        for name in FAMILIES:
            tr, te = f != name, f == name
            Xt = np.vstack([X[tr], Xh_tr]); yt = np.concatenate([y[tr], np.zeros(len(Xh_tr))])
            p = fit_score(Xt, yt, X[te]); yte = y[te]
            fam[name][5].append(recall_at_fpr(yte, p, 0.05))
            fam[name][10].append(recall_at_fpr(yte, p, 0.10))
        Xt = np.vstack([X, Xh_tr]); yt = np.concatenate([y, np.zeros(len(Xh_tr))])
        tau = np.quantile(fit_score(Xt, yt, Xh_cal), 0.90)
        hon.append((fit_score(Xt, yt, Xh_tst) >= tau).mean())
    print(f"\n[held-out family, honest-trained, K={K} draws]  recall at a false-alarm budget (the honest metric)")
    for name in FAMILIES:
        print(f"  {name:<10} recall@FPR5% {ms(fam[name][5])}  recall@FPR10% {ms(fam[name][10])}")
    print(f"[honest-only, 10% budget, out-of-sample]  FPR {ms(hon)}  (calibrated on separate clean worlds)")

def honest_dataset(n_worlds, seed):
    rng = random.Random(seed)
    X = []
    for _ in range(n_worlds):
        ent, truth = entities_and_truth(make_run(disguised_scheme(rng, n_dirty=0)))
        feats = build_features(ent)
        assert all(truth[i]["label"] != "corrupt" for i in ent), "honest world planted a corrupt node"
        X.extend(feats[i] for i in ent)
    return np.array(X, float)
def feature_stability(X, y, fam, delta=0.05):
    print(f"\n[feature stability]  keep a feature only if its signal agrees across families (|AUC-0.5| > {delta}, same side)")
    for j, name in enumerate(FEATURES_NAMES):
        aucs = {}
        for fm in FAMILIES:
            m = fam == fm
            col = X[m][:, j]
            aucs[fm] = roc_auc_score(y[m], col) if len(set(col.tolist())) > 1 else None
        vals = [a for a in aucs.values() if a is not None]
        if len(vals) < 2:
            print(f"  {name:<14} only in {len(vals)} family — can't judge stability"); continue
        lo, hi = min(vals), max(vals)
        if lo > 0.5 + delta or hi < 0.5 - delta:
            tag = "KEEP (stable)"
        elif lo < 0.5 - delta and hi > 0.5 + delta:
            tag = "DROP (sign flips)"
        else:
            tag = "weak"
        row = "  ".join(f"{fm[:4]} {aucs[fm]:.2f}" if aucs[fm] is not None else f"{fm[:4]} --" for fm in FAMILIES)
        print(f"  {name:<14} {row}   -> {tag}")
def main():
    X, y, w, f = dataset(n_worlds=30, seed=0)
    print(f"dataset: {len(y)} rows, {int(y.sum())} corrupt ({y.mean():.1%}), {len(set(w.tolist()))} worlds\n")
    single_feature_auc(X, y)
    leak_audit(X, y)
    feature_stability(X, y, f)

    K = 10
    roc = pr = fpr = None
    accs = {"roc": [], "pr": [], "fpr": []}
    for s in range(K):
        Xtr, ytr, Xte, yte = split_by_world(X, y, w, seed=s)
        r, p, fp = metrics(yte, fit_score(Xtr, ytr, Xte))
        accs["roc"].append(r); accs["pr"].append(p); accs["fpr"].append(fp)

    Xtr, ytr, Xte, yte = split_by_world(X, y, w, seed=0)
    sh = []
    for s in range(K):
        ysh = ytr.copy(); np.random.RandomState(s).shuffle(ysh)
        sh.append(roc_auc_score(yte, fit_score(Xtr, ysh, Xte)))
    print(f"\n[label-shuffle x{K}, fixed split]  ROC-AUC {ms(sh)}  (expect ~0.5; higher => leak)")
    print(f"[seed-split x{K} world-splits]     ROC-AUC {ms(accs['roc'])}")
    print(f"                                   PR-AUC  {ms(accs['pr'])}")
    print(f"                                   FPR     {ms(accs['fpr'])}")
    held_out_ci()

if __name__ == "__main__":
    main()
