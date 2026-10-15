import glob, json
import numpy as np
from sklearn.metrics import roc_auc_score

def num(x): return (x.get("netAmountEur") or x.get("netAmount")) if isinstance(x,dict) else None

def bid_count(lots):
    bcs = [l.get("bidsCount") for l in lots if isinstance(l.get("bidsCount"), (int, float))]
    return max(bcs) if bcs else None

def main():
    rows = []
    for f in sorted(glob.glob("data/data-ro-2015.ndjson")):
        for line in open(f, encoding="utf-8"):
            line = line.strip()
            if not line: continue
            t = json.loads(line)
            lots = t.get("lots") or []
            if sum(len(l.get("bids") or []) for l in lots) == 0: continue
            bc = bid_count(lots)
            single = int(bc == 1) if bc is not None else 0
            nonopen = 0 if t.get("procedureType") == "OPEN" else 1
            est, fin = num(t.get("estimatedPrice")), num(t.get("finalPrice"))
            wp_c = wp_f = 0
            if est and fin and est > 0 and 0.3 <= fin/est <= 1.3:
                wp_c = 1; wp_f = int(fin/est >= 0.98)
            iv, dc = [], []
            for i in (t.get("indicators") or []):
                ty = i.get("type")
                if not ty.startswith("INTEGRITY") or i.get("status") != "CALCULATED": continue
                v = i.get("value")
                if v is None: continue
                iv.append(v)
                if ty not in ("INTEGRITY_SINGLE_BID", "INTEGRITY_PROCEDURE_TYPE"): dc.append(v)
            rows.append((single, nonopen, wp_f, wp_c,
                         np.mean(iv) if iv else None, np.mean(dc) if dc else None))
    R = [r for r in rows if r[4] is not None]
    comp = np.array([r[4] for r in R]); low = (comp < np.median(comp)).astype(int)
    fc = np.array([r[0] + r[1] + r[2] for r in R])
    print(f"RO 2015 awarded with composite: {len(R)}")
    print(f"flag rates: single(bidsCount) {np.mean([r[0] for r in R]):.3f}  "
          f"non-open {np.mean([r[1] for r in R]):.3f}  winner-prem {np.mean([r[2] for r in R]):.3f}")
    print(f"FULL concordance  AUC(3-flag vs low-integrity) = {roc_auc_score(low, fc):.3f}")
    RD = [r for r in R if r[3] == 1 and r[5] is not None]
    cdc = np.array([r[5] for r in RD]); lowdc = (cdc < np.median(cdc)).astype(int)
    wp = np.array([r[2] for r in RD])
    print(f"DE-CIRC (winner-prem only vs integrity w/o single-bid+procedure) n={len(RD)}  AUC = {roc_auc_score(lowdc, wp):.3f}")

if __name__ == "__main__":
    main()
