from __future__ import annotations
import random
from world import make_run
from ingest import entities_and_truth
from ml import Learner, detect
from features import build_features
from oracle import attest, reconcile, wealth_reconciliation
from schemes import ghost, kickback, embezzle, ektp, launder
from breed import breed
from laundering import run_laundering

COVERAGE = 0.9


def valid(model):
    try:
        run = make_run(model)
        return abs(run["nodes"][0]["received"] - model["appropriation"]) < 1
    except Exception:
        return False


def xy(model):
    run = make_run(model)
    ent, truth = entities_and_truth(run)
    feats = build_features(ent)
    X = [feats[i] for i in ent]
    y = [1 if truth[i]["label"] == "corrupt" else 0 for i in ent]
    return run, ent, truth, X, y


def detect_all(run, ent, learner, cov, rng):
    flagged = detect(ent, learner)
    flagged |= {f.entity for f in wealth_reconciliation(ent)}
    flagged |= {f.entity for f in run_laundering(ent)}
    if cov > 0:
        flagged |= {f.entity for f in reconcile(run, attest(run, coverage=cov, rng=rng))}
    return flagged


def measure(models, learner, cov, rng):
    tp = fn = fp = 0
    for m in models:
        run, ent, truth, _, _ = xy(m)
        flagged = detect_all(run, ent, learner, cov, rng)
        for i in ent:
            c = truth[i]["label"] == "corrupt"
            h = i in flagged
            tp += c and h
            fn += c and not h
            fp += (not c) and h
    rec = tp / (tp + fn) if tp + fn else 1.0
    prec = tp / (tp + fp) if tp + fp else 1.0
    return rec, prec


def main():
    rng = random.Random(0)
    orng = random.Random(1)
    holdout = [ektp(), launder()]
    pop = [ghost(), kickback(), embezzle()]
    learner = Learner()
    X, y = [], []

    print(f"seed: ghost, kickback, embezzle   |   holdout: e-KTP, laundering   |   audit coverage: {COVERAGE:.0%}\n")
    r0, p0 = measure(holdout, None, 0, orng)
    ro, po = measure(holdout, None, COVERAGE, orng)
    print(f"rules only             holdout recall {r0:.0%}  precision {p0:.0%}")
    print(f"rules + oracle audit   holdout recall {ro:.0%}  precision {po:.0%}\n")
    print("round  pop  train_rows  holdout(+ML+oracle)  worst_evasion")

    for rnd in range(8):
        pop = [m for m in pop if valid(m)]
        scored = []
        for m in pop:
            run, ent, truth, Xi, yi = xy(m)
            flagged = detect_all(run, ent, learner, COVERAGE, orng)
            missed = sum(truth[i]["label"] == "corrupt" and i not in flagged for i in ent)
            scored.append((missed, m))
            X += Xi
            y += yi
        learner.train(X, y)
        scored.sort(key=lambda s: -s[0])
        rec, prec = measure(holdout, learner, COVERAGE, orng)
        print(f"{rnd:>5}  {len(pop):>3}  {len(X):>10}    recall {rec:>4.0%} prec {prec:>4.0%}    hid {scored[0][0]}")
        parents = [m for _, m in scored[:6]]
        pop = parents + breed(parents, rng, n=24)


if __name__ == "__main__":
    main()
