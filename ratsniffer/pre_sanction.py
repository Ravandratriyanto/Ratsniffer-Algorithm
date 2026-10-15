import sys, glob, json, re
import numpy as np
from collections import Counter
from sklearn.metrics import roc_auc_score
from eval import ms

BLACKLIST = {"SIVECO","INTRAROM","ENERGOBIT","ELECTROMAGNETICA","CONDMAG","ARMAX","OYL","ELECTRICA"}
WORD = {"ELECTRICA","OYL","ARMAX"}
SANCTION_YEAR = {}
FEAT = ["single_rate","buyer_hhi","market_dominance","market_hhi","win_premium_rate"]

def norm(s): return " " + re.sub(r"[^A-Z0-9 ]"," ",(s or "").upper()) + " "

def blacklisted(name):
    u = norm(name)
    return any((re.search(r"\b"+t+r"\b",u) if t in WORD else t in u) for t in BLACKLIST)

def num(x): return (x.get("netAmountEur") or x.get("netAmount")) if isinstance(x,dict) else None

def cpv_div(lots):
    for l in lots:
        for c in (l.get("cpvs") or []):
            if c.get("code"): return c["code"][:2]
    return None

def scan(paths, year_lt):
    firms, mt, mf = {}, Counter(), {}
    for f in paths:
        for line in open(f, encoding="utf-8"):
            line = line.strip()
            if not line: continue
            t = json.loads(line)
            try: yr = int(t.get("tenderYear"))
            except (TypeError, ValueError): yr = None
            if yr is None or yr >= year_lt: continue
            lots = t.get("lots") or []
            nb = sum(len(l.get("bids") or []) for l in lots)
            if nb == 0: continue
            div = cpv_div(lots)
            by = (t.get("buyers") or [{}])[0]; buyer = by.get("id") or by.get("name")
            est, fin = num(t.get("estimatedPrice")), num(t.get("finalPrice"))
            wp_c = wp_f = 0
            if est and fin and est > 0:
                r = fin / est
                if 0.3 <= r <= 1.3: wp_c, wp_f = 1, int(r >= 0.98)
            winners = {bd["name"].strip().upper()
                       for l in lots for b in (l.get("bids") or []) if b.get("isWinning")
                       for bd in (b.get("bidders") or []) if bd.get("name")}
            if div is not None: mt[div] += 1
            for w in winners:
                fr = firms.setdefault(w, {"wins":0,"single":0,"buyers":Counter(),"divs":Counter(),"wp_c":0,"wp_f":0})
                fr["wins"] += 1; fr["single"] += int(nb == 1)
                if buyer: fr["buyers"][buyer] += 1
                if div is not None:
                    fr["divs"][div] += 1; mf.setdefault(div, Counter())[w] += 1
                fr["wp_c"] += wp_c; fr["wp_f"] += wp_f
    return firms, mt, mf

def features(firms, mt, mf, T, min_wins=20):
    names, X, y, meta = [], [], [], []
    for name, fr in firms.items():
        n = fr["wins"]
        if n < min_wins: continue
        if SANCTION_YEAR:
            sy = SANCTION_YEAR.get(name)
            if blacklisted(name) and (sy is None or sy < T): continue
        buyer_hhi = sum((c/n)**2 for c in fr["buyers"].values())
        dv, _ = fr["divs"].most_common(1)[0] if fr["divs"] else (None, 0)
        dom = (mf.get(dv,{}).get(name,0)/mt[dv]) if dv and mt[dv] else 0.0
        mhhi = sum((c/mt[dv])**2 for c in mf.get(dv,{}).values()) if dv and mt[dv] else 0.0
        wp = fr["wp_f"]/fr["wp_c"] if fr["wp_c"] else 0.0
        names.append(name); X.append([fr["single"]/n, buyer_hhi, dom, mhhi, wp])
        y.append(int(blacklisted(name))); meta.append((n, dv))
    return names, np.array(X, float), np.array(y), meta

def matched_controls(X, y, score, meta):
    above = []
    for i in np.where(y == 1)[0]:
        n_i, dv_i = meta[i]
        ctrl = [score[j] for j in range(len(y))
                if y[j] == 0 and meta[j][1] == dv_i and 0.5*n_i <= meta[j][0] <= 2*n_i]
        if ctrl: above.append(score[i] > np.median(ctrl))
    return above

def run(T):
    firms, mt, mf = scan(sorted(glob.glob("data/data-ro-20*.ndjson")), year_lt=T)
    names, X, y, meta = features(firms, mt, mf, T)
    if len(set(y.tolist())) < 2:
        print(f"T={T}: no positives with pre-{T} activity"); return
    z = (X - X.mean(0)) / (X.std(0) + 1e-9); score = z.sum(1)
    auc = roc_auc_score(y, score)
    sh = [roc_auc_score(np.random.RandomState(s).permutation(y), score) for s in range(20)]
    ctrl = matched_controls(X, y, score, meta)
    order = np.argsort(-score); rank = {i: r for r, i in enumerate(order)}
    print(f"\n=== T={T}  (features from tenders < {T}) ===")
    print(f"firms >=20 pre-{T} wins: {len(names)}  positives: {int(y.sum())}")
    print(f"HHI cartel score AUC vs blacklist = {auc:.3f}")
    print(f"label-shuffle x20 AUC {ms(sh)}  (expect ~0.5)")
    if ctrl:
        print(f"matched-control: {sum(ctrl)}/{len(ctrl)} positives beat their sector+size control median")
    for i in np.where(y == 1)[0]:
        print(f"  {names[i][:26]:26s} score {score[i]:+.2f}  pct {1 - rank[i]/len(names):.2f}")

if __name__ == "__main__":
    Ts = [int(a) for a in sys.argv[1:]] or [2012, 2014, 2016]
    if not SANCTION_YEAR:
        print("WARNING: SANCTION_YEAR empty -> running WITHOUT real sanction dates (exploratory, not a true pre-sanction test)")
    for T in Ts: run(T)
