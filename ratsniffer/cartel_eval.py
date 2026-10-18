import json, hashlib
from collections import Counter
import numpy as np
from sklearn.metrics import roc_auc_score
from sklearn.ensemble import IsolationForest
from procurement import tender_features, PROC_FEATURES
from eval import fit_score, recall_at_fpr, ms

def load(path="data/prozorro_ua.ndjson"):
    X, y, c = [], [], []
    for line in open(path, encoding="utf-8"):
        line = line.strip()
        if not line: continue
        try:
            r = json.loads(line)
        except json.JSONDecodeError:
            continue
        est, bids = r.get("estimate"), r.get("bids") or []
        if not est or len(bids) < 2: continue
        X.append(tender_features({"bids": bids, "estimate": est}))
        hits = r.get("cartel_hits") or []
        y.append(1 if hits else 0)
        c.append(hits[0].split("::")[0] if hits else "")
    return np.array(X, float), np.array(y), np.array(c)

def cobidder_hhi(path):
    firm_co = {}
    for line in open(path, encoding="utf-8"):
        line = line.strip()
        if not line: continue
        try:
            r = json.loads(line)
        except json.JSONDecodeError:
            continue
        eds = [e for e in (r.get("bidders") or []) if e]
        for e in eds:
            firm_co.setdefault(e, Counter()).update(b for b in eds if b != e)
    hhi = {}
    for firm, co in firm_co.items():
        total = sum(co.values())
        hhi[firm] = sum((v / total) ** 2 for v in co.values()) if total else 0.0
    return hhi

def prec_at_k(y, scores, k):
    return y[np.argsort(scores)[::-1][:k]].mean()
def firm_win_rate(path):
    appeared = {}
    won = {}
    for line in open(path, encoding="utf-8"):
        r = json.loads(line.strip())
        bids = r.get("bids_detail") or []
        winner = r.get("winner")
        for firm in (r.get("bidders") or []):
            appeared[firm] = appeared.get(firm, 0) + 1
            if firm == winner:
                won[firm] = won.get(firm, 0) + 1
    return {f: won.get(f, 0) / n for f, n in appeared.items() if n >= 5}

def pct_chronic_losers(bidders, rates, threshold=0.05):
    eligible = [b for b in bidders if b in rates]
    if not eligible:
        return 0.0
    return sum(1 for b in eligible if rates[b] < threshold) / len(eligible)
def main():
    path = "data/prozorro_ua.ndjson"
    X, y, c = load(path)
    n, pos = len(y), int(y.sum())
    print(f"lots {n}  cartel-tagged {pos}  clean {n - pos}")
    if pos < 3:
        print("too few cartel-tagged lots to test yet (batch still finding them)"); return
    cartels = sorted(set(c[c != ""]))
    print("cartels:", {k: int((c == k).sum()) for k in cartels})

    print("\n[per-screen AUC: cartel-tagged vs clean]")
    active = [j for j in range(X.shape[1]) if len(set(X[:, j].tolist())) > 1]
    for j in active:
        a = roc_auc_score(y, X[:, j])
        flag = "  <-- separates (check if artifact)" if a > 0.9 or a < 0.1 else ""
        print(f"  {PROC_FEATURES[j]:16} {a:.3f}{flag}")

    print("\n[precision@k on bid_cv]")
    cv_scores = X[:, PROC_FEATURES.index("bid_cv")]
    for k in [10, 20, 50]:
        print(f"  @{k:>3}: {prec_at_k(y, cv_scores, k):.3f}  (base rate {y.mean():.3f})")

    X_clean = X[y == 0]
    iso = IsolationForest(n_estimators=200, contamination="auto", random_state=42).fit(X_clean)
    iso_s = -iso.score_samples(X)
    print(f"\n[IsolationForest on clean-only]  AUC {roc_auc_score(y, iso_s):.3f}  recall@FPR10% {recall_at_fpr(y, iso_s, 0.10):.3f}")
    sh_iso = []
    for s in range(20):
        ys = y.copy(); np.random.RandomState(s).shuffle(ys)
        X_c = X[ys == 0]
        iso2 = IsolationForest(n_estimators=200, contamination="auto", random_state=s).fit(X_c)
        sh_iso.append(roc_auc_score(ys, -iso2.score_samples(X)))
    print(f"[iso shuffle x20] {ms(sh_iso)}  (expect ~0.5)")

    sh = []
    for s in range(20):
        ys = y.copy(); np.random.RandomState(s).shuffle(ys)
        sh.append(max(roc_auc_score(ys, X[:, j]) for j in active))
    print(f"[label-shuffle x20] best single-screen AUC {ms(sh)}  (expect ~0.5-0.6)")

    print("\n[co-bidder HHI: top concentrated firms]")
    hhi = cobidder_hhi(path)
    top = sorted(hhi.items(), key=lambda x: -x[1])[:10]
    for firm, h in top:
        print(f"  {firm}  HHI {h:.3f}")

    if len(cartels) >= 2:
        print("\n[leave-one-cartel-out]  train other cartels + clean, test held-out cartel vs clean")
        cl = np.where(y == 0)[0]
        h = np.array([int(hashlib.md5(str(i).encode()).hexdigest(), 16) % 2 for i in cl])
        cl_tr, cl_te = cl[h == 0], cl[h == 1]
        for k in cartels:
            pk = np.where(c == k)[0]
            otr = np.where((y == 1) & (c != k))[0]
            if len(otr) < 2 or len(pk) < 2:
                print(f"  {k:22} n_pos={len(pk)}  (skip: too few)"); continue
            Xtr = np.vstack([X[otr], X[cl_tr]]); ytr = np.r_[np.ones(len(otr)), np.zeros(len(cl_tr))]
            Xte = np.vstack([X[pk], X[cl_te]]); yte = np.r_[np.ones(len(pk)), np.zeros(len(cl_te))]
            p = fit_score(Xtr, ytr, Xte)
            print(f"  {k:22} n_pos={len(pk):4}  AUC {roc_auc_score(yte, p):.3f}  recall@FPR10% {recall_at_fpr(yte, p, 0.10):.3f}")
    else:
        print(f"\nonly one cartel ({cartels[0]}) in this pull -> the per-screen AUC above is the signal;")
        print("leave-one-cartel-out needs the other cartels' windows pulled too.")

    print("\nCAVEAT (dilution): labels are firm-level — every tender a cartel firm bid on is tagged,")
    print("but only a few were the actually-rigged ones. Near-chance is the dilution ceiling,")
    print("not proof the screens fail; exact rigged-tender IDs (AMCU PDFs, 403-blocked) would de-dilute.")

if __name__ == "__main__":
    main()
