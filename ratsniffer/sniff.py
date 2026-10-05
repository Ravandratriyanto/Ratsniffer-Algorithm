import os
from ingest import load_run, build_ledger
from gates import run_gates
from analyzer import run_analyzer
from oracle import wealth_reconciliation
from laundering import run_laundering
from journal import Journal, cross_check

HERE = os.path.dirname(__file__)
RUN_PATH = os.path.join(HERE, "run.json")
JOURNAL_PATH = os.path.join(HERE, "journal.jsonl")

if os.path.exists(JOURNAL_PATH):      # one journal per run; it appends otherwise
    os.remove(JOURNAL_PATH)
jr = Journal(JOURNAL_PATH)

cons, entities, truth = build_ledger(load_run(RUN_PATH), journal=jr)
canon = cons.canonical()
print(f"consortium: {len(cons.validators)} validators (quorum {cons.quorum})  |  canonical chain: {len(canon.chain) if canon else 'NONE'} blocks")

ok, why = jr.verify()
entries = jr.load()
print(f"journal: {len(entries)} entries ({sum(e.kind == 'txn' for e in entries)} txn)  "
      f"|  verify: {'OK' if ok else why}")
if canon:
    diff = cross_check(jr, canon)
    print(f"cross-check vs chain: {'agree' if not diff else chr(10) + chr(10).join('  ' + d for d in diff)}")

flags = run_gates(entities) + run_analyzer(entities) + wealth_reconciliation(entities) + run_laundering(entities)
flagged = {f.entity for f in flags}
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