from ingest import load_run, build_ledger
from gates import run_gates
from analyzer import run_analyzer
from oracle import wealth_reconciliation
from laundering import run_laundering
bc, entities, truth = build_ledger(load_run("run.json"))
ok, reason = bc.verify_chain()
print(f"ledger: {len(bc.chain)} blocks  |  chain valid: {ok}")

flags = run_gates(entities) + run_analyzer(entities)
flagged = {f.entity for f in flags}
flags = run_gates(entities) + run_analyzer(entities) + wealth_reconciliation(entities) + run_laundering(entities)
print("\nFLAGS")
for f in sorted(flags, key=lambda f: -f.severity):
    print(f"  {entities[f.entity]['name']:<28} {f.detector:<18} sev {f.severity:.2f}  {f.detail}")

print("\nSCORECARD  (all flags vs ground-truth label)")
tp = fp = fn = 0
for eid, e in entities.items():
    lab = truth[eid]["label"]
    hit = eid in flagged
    if lab == "corrupt":
        mark = "caught" if hit else ">>> MISSED <<<"
        tp += hit
        fn += not hit
    else:
        mark = "FALSE POSITIVE" if hit else "ok (clean)"
        fp += hit
    print(f"  {e['name']:<28} truth={lab:<8} {mark}")

prec = tp / (tp + fp) if (tp + fp) else 0
rec = tp / (tp + fn) if (tp + fn) else 0
print(f"\nprecision {prec:.0%}  recall {rec:.0%}")