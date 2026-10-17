import json, hashlib
import numpy as np
from sklearn.metrics import roc_auc_score
from procurement import tender_features, PROC_FEATURES
from eval import fit_score, recall_at_fpr, ms

def load(path="data/prozorro_ua.ndjson"):
    X, y, c = [], [], []
    for line in open(path, encoding="utf-8"):
        line = line.strip()
        if not line: continue
        r = json.loads(line)
        est, bids = r.get("estimate"), r.get("bids") or []
        if not est or len(bids) < 2: continue
        X.append(tender_features({"bids": bids, "estimate": est}))
        hits = r.get("cartel_hits") or []
        y.append(1 if hits else 0)
        c.append(hits[0].split("::")[0] if hits else "")
    return np.array(X, float), np.array(y), np.array(c)

def main():
    X, y, c = load()
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

    sh = []
    for s in range(20):
        ys = y.copy(); np.random.RandomState(s).shuffle(ys)
        sh.append(max(roc_auc_score(ys, X[:, j]) for j in active))
    print(f"[label-shuffle x20] best single-screen AUC {ms(sh)}  (expect ~0.5-0.6)")

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
