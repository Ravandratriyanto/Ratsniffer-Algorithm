import random 
import numpy as np 
from sklearn.metrics import roc_auc_score 
from eval import fit_score, recall_at_fpr, split_by_world, ms 

PROC_FEATURES = ["single_bid", "bid_cv", "winner_premium", "n_bidders"]

def procurement_world(rng, n_tenders=25, p_rig=0.25):
    tenders = []
    for _ in range(n_tenders):
        est = rng.choice([1e8, 5e8, 1e9]) * rng.uniform(0.5, 1.5)
        rigged = rng.random() < p_rig
        if not rigged: 
            k = rng.random() < p_rig 
            bids = [est * rng.uniform(0.6, 0.98)for _ in range(k)]
        elif rng.random() < 0.4:
            k = 1
            bids = [est * rng.uniform(0.6, 0.98) for _ in range(k)]
        elif rng.random() < 0.4:
            k = rng.randint(3, 5)
            win = est * rng.uniform(0.93, 0.99)
            bids = [win] + [win * rng.uniform(1.0, 1.03) for _ in range(k - 1)]
        tenders.append({"bids": bids, "estimate": est, "label": "corrupt" if rigged else "clean"})
    return tenders

def tender_features(t):
    b = t["bids"]; k = len(b); mu = sum(b) / k 
    cv = (sum((x - mu) ** 2 for x in b) / k) ** 0.5 / mu if mu and k > 1 else 0.0
    return [1.0 if k == 1 else 0.0, cv, min(b) / t["estimate"], float(k)]
def dataset(n_worlds, seed):
    rng = random.Random(seed)
    X, y, w = [], [], []
    for wid in range(n_worlds):
        for t in procurement_world(rng):
            X.append(tender_features(t)); y.append(1 if t["label"] == "corrupt" else 0); w.append(wid)
    return np.array(X, float), np.array(y), np.array(w)
def procurement_world(rng, n_tenders=25, p_rig=0.25):
    tenders = []
    for _ in range(n_tenders):
        est = rng.choice([1e8, 5e8, 1e9]) * rng.uniform(0.5, 1.5)
        rigged = rng.random() < p_rig
        if not rigged:
            k = rng.randint(3, 6)
            bids = [est * rng.uniform(0.6, 0.98) for _ in range(k)]
        elif rng.random() < 0.4:
            k = 1
            bids = [est * rng.uniform(0.95, 1.0)]
        else:
            k = rng.randint(3, 5)
            win = est * rng.uniform(0.93, 0.99)
            bids = [win] + [win * rng.uniform(1.0, 1.03) for _ in range(k - 1)]
        tenders.append({"bids": bids, "estimate": est, "label": "corrupt" if rigged else "clean"})
    return tenders
def main():
    X, y, w = dataset(30, seed=0)
    print(f"procurement: {len(y)} tenders, {int(y.sum())} rigged ({y.mean():.1%}), {len(set(w.tolist()))} buyers\n")
    print("[single-feature AUC]")
    for j, name in enumerate(PROC_FEATURES):
        col = X[:, j]
        if len(set(col.tolist())) > 1:
            print(f"  {name:<16} {roc_auc_score(y, col):.3f}")
    roc = []; r5 = []; r10 = []; sh = []
    for s in range(10):
        Xtr, ytr, Xte, yte = split_by_world(X, y, w, seed=s)
        p = fit_score(Xtr, ytr, Xte)
        roc.append(roc_auc_score(yte, p)); r5.append(recall_at_fpr(yte, p, 0.05)); r10.append(recall_at_fpr(yte, p, 0.10))
    Xtr, ytr, Xte, yte = split_by_world(X, y, w, seed=0)
    for s in range(10):
        ysh = ytr.copy(); np.random.RandomState(s).shuffle(ysh)
        sh.append(roc_auc_score(yte, fit_score(Xtr, ysh, Xte)))
    print(f"\n[held-out by buyer x10]  ROC {ms(roc)}")
    print(f"                         recall@FPR5%  {ms(r5)}")
    print(f"                         recall@FPR10% {ms(r10)}")
    print(f"[label-shuffle x10]      ROC {ms(sh)}  (expect ~0.5)")

if __name__ == "__main__":
    main()


