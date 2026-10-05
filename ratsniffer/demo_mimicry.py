import random
from world import make_run
from ingest import entities_and_truth
from ml import Learner, detect
from features import build_features
from adversary import random_scheme, disguised_scheme

rng = random.Random(0)

learner = Learner()
X, y = [], []
for _ in range(40):
    ent, truth = entities_and_truth(make_run(random_scheme(rng)))
    feats = build_features(ent)
    for i in ent:
        X.append(feats[i]); y.append(1 if truth[i]["label"] == "corrupt" else 0)
learner.train(X, y)

tp = fn = 0
for _ in range(20):
    ent, truth = entities_and_truth(make_run(disguised_scheme(rng)))
    flagged = detect(ent, learner)
    for i in ent:
        if truth[i]["label"] != "corrupt":
            continue
        tp += i in flagged
        fn += i not in flagged

rec = tp / (tp + fn) if tp + fn else 0
print(f"disguised-corruption recall: {rec:.0%}  ({tp} caught / {tp + fn} planted)")
