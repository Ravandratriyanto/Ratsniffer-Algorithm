import glob, json, re, csv
import numpy as np
from sklearn.metrics import roc_auc_score
from eval import recall_at_fpr

def num(x): return (x.get("netAmountEur") or x.get("netAmount")) if isinstance(x,dict) else None

def bid_count(lots):
    bcs = [l.get("bidsCount") for l in lots if isinstance(l.get("bidsCount"), (int, float))]
    return max(bcs) if bcs else None

def cpv_div(lots):
    for l in lots:
        for c in (l.get("cpvs") or []):
            if c.get("code"): return c["code"][:2]
    return None

def year4(s):
    m = re.match(r"\s*(\d{4})", s or "")
    return int(m.group(1)) if m else None

def load_sanctions(path):
    firms = []
    with open(path, encoding="utf-8") as fh:
        for row in csv.DictReader(fh):
            if row["role"].strip() == "organiser-buyer": continue
            tok = re.findall(r"[A-Za-z0-9]+", row["firm"])
            if not tok: continue
            firms.append({"name": row["firm"], "tok": tok[0].upper(),
                          "start": year4(row["infr_start"]), "end": year4(row["infr_end"])})
    return firms

def matches(firms, name, year):
    u = " " + re.sub(r"[^A-Z0-9 ]", " ", name.upper()) + " "
    out = []
    for fr in firms:
        t = fr["tok"]
        m = re.search(r"\b" + re.escape(t) + r"\b", u) if len(t) <= 4 else (t in u)
        if m:
            inwin = fr["start"] is not None and fr["end"] is not None and fr["start"] <= year <= fr["end"]
            out.append((fr["tok"], inwin))
    return out

def main():
    firms = load_sanctions("data/sanctions.csv")
    recs, cov = [], {}
    for f in sorted(glob.glob("data/data-ro-20*.ndjson")):
        for line in open(f, encoding="utf-8"):
            line = line.strip()
            if not line: continue
            t = json.loads(line)
            lots = t.get("lots") or []
            nb = sum(len(l.get("bids") or []) for l in lots)
            if nb == 0: continue
            try: yr = int(t.get("tenderYear"))
            except (TypeError, ValueError): continue
            div = cpv_div(lots)
            est, fin = num(t.get("estimatedPrice")), num(t.get("finalPrice"))
            wp_f = int(bool(est and fin and est > 0 and 0.3 <= fin/est <= 1.3 and fin/est >= 0.98))
            nonopen = 0 if t.get("procedureType") == "OPEN" else 1
            bc = bid_count(lots)
            single = int(bc == 1) if bc is not None else 0
            winners = {bd["name"].strip() for l in lots for b in (l.get("bids") or [])
                       if b.get("isWinning") for bd in (b.get("bidders") or []) if bd.get("name")}
            sanctioned = inwin = False
            for w in winners:
                for tok, iw in matches(firms, w, yr):
                    sanctioned = True
                    if iw:
                        inwin = True; cov[tok] = cov.get(tok, 0) + 1
            recs.append((yr, div, single + nonopen + wp_f, sanctioned, inwin))
    pos = [r for r in recs if r[4]]
    cells = {(r[0], r[1]) for r in pos}
    ctrl = [r for r in recs if not r[3] and (r[0], r[1]) in cells]
    print(f"scanned {len(recs)} awarded RO tenders")
    print("\n[infringement-window contracts found per firm]  (label-coverage reality check)")
    for fr in firms:
        print(f"  {fr['name'][:24]:24s} {fr['start']}-{fr['end']}  found {cov.get(fr['tok'], 0)}")
    print(f"\npositives (sanctioned firm, in infringement window) {len(pos)}")
    print(f"matched controls (same CPV-div + year, clean winner) {len(ctrl)}")
    if len(pos) < 5 or len(ctrl) < 5:
        print("-> too few to test; label coverage is the finding")
        return
    y = np.array([1]*len(pos) + [0]*len(ctrl))
    s = np.array([r[2] for r in pos] + [r[2] for r in ctrl], float)
    print(f"combined-flag mean: positives {s[:len(pos)].mean():.2f}  controls {s[len(pos):].mean():.2f}")
    print(f"AUC(label vs combined flag) = {roc_auc_score(y, s):.3f}")
    print(f"recall@FPR10% = {recall_at_fpr(y, s, 0.10):.3f}")
    sh = [roc_auc_score(np.random.RandomState(k).permutation(y), s) for k in range(20)]
    print(f"label-shuffle x20 AUC {np.mean(sh):.3f}+/-{np.std(sh):.3f}  (expect ~0.5)")

if __name__ == "__main__":
    main()
