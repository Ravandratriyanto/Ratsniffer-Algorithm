import os
import numpy as np
from sklearn.preprocessing import StandardScaler
from collections import defaultdict
from ingest import load_run, build_ledger
from ml import Learner
from features import build_features, FEATURES_NAMES
from gates import run_gates
from laundering import run_laundering
from eval import dataset, honest_dataset
from oracle import wealth_reconciliation
from analyzer import run_analyzer

HERE = os.path.dirname(__file__)

def main():
    cons, entities, truth = build_ledger(load_run(os.path.join(HERE, "run.json")))

    Xtr, ytr, *_ = dataset(n_worlds=20, seed=0)
    Xh = honest_dataset(n_worlds=20, seed=2)
    Xtr = np.vstack([Xtr, Xh]); ytr = np.concatenate([ytr, np.zeros(len(Xh))])
    sc = StandardScaler().fit(Xtr)
    lrn = Learner(); lrn.train(sc.transform(Xtr), ytr)
    TAU = float(np.quantile(lrn.predict(sc.transform(Xh)), 0.90))
    feats = build_features(entities)
    ids = list(feats.keys())
    Xent = dict(zip(ids, sc.transform([feats[i] for i in ids])))
    probs = dict(zip(ids, lrn.predict([Xent[i] for i in ids])))
    anom = dict(zip(ids, lrn.anomaly([Xent[i] for i in ids])))
    coef = lrn.clf.coef_[0]
    def why(i):
        c = sorted(zip(FEATURES_NAMES, coef, Xent[i]), key=lambda t: -t[1] * t[2])
        return [f"{name} ({w * v:+.2f})" for name, w, v in c[:3] if w * v > 0]
    byent = defaultdict(list)
    for f in run_gates(entities) + run_analyzer(entities) + wealth_reconciliation(entities) + run_laundering(entities):
        byent[f.entity].append(f)
    nm = lambda x: entities.get(x, {}).get("name", x)
    print("TRANSACTIONS")
    canon = cons.canonical()
    for b in (canon.chain if canon else []):
        for t in b.txns:
            print(f"  {nm(t.sender):<24} -> {nm(t.recipient):<24} {t.amount:>18,.0f}  {t.type.value}")

    print(f"\nDETECTION REPORT  (trained on scheme + honest worlds; ML threshold {TAU:.2f} = ~10% false alarms on clean worlds)")
    for i in sorted(ids, key=lambda i: -probs[i]):
        rules = byent.get(i, [])
        verdict = "CORRUPT" if (probs[i] >= TAU or rules) else "clean"
        print(f"\n  {nm(i):<26} ML p={probs[i]:.2f}  anomaly={anom[i]:.2f}  -> {verdict}   [truth={truth[i]['label']}]")
        reasons = why(i)
        print(f"      why: {', '.join(reasons) if reasons else '(nothing pushing toward corrupt)'}")
        for f in rules:
            print(f"      flag {f.detector:<18} sev {f.severity:.2f}  {f.detail}")

if __name__ == "__main__":
    main()
