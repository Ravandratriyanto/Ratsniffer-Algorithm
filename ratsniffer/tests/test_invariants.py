import random

import numpy as np
from sklearn.metrics import roc_auc_score

from world import make_run
from ingest import entities_and_truth
from features import build_features, FEATURES_NAMES
from eval import dataset, fit_score, split_by_world
from adversary import random_scheme, disguised_scheme, cascade_scheme

FAMILIES = (random_scheme, disguised_scheme, cascade_scheme)


def _runs(n=5, seed=0):
    rng = random.Random(seed)
    for gen in FAMILIES:
        for _ in range(n):
            yield make_run(gen(rng))


def test_conservation():
    for run in _runs():
        for n in run["nodes"]:
            bal = n["diverted"] + n["retained"] + n["down"] + n["delivered"] + n["kickedOut"]
            assert abs(n["received"] - bal) <= max(1.0, n["received"]) * 1e-6


def test_cashout_identity():
    for run in _runs():
        for n in run["nodes"]:
            assert abs(n["cashedOut"] - (n["delivered"] + n["diverted"])) <= max(1.0, n["received"]) * 1e-6


def test_feature_vector_length_matches_names():
    for run in _runs(n=2):
        ent, _ = entities_and_truth(run)
        for v in build_features(ent).values():
            assert len(v) == len(FEATURES_NAMES)


def test_entities_hide_ground_truth():
    forbidden = {"label", "trueDelivered", "schemes", "corrupt", "effectiveCapture", "diverted"}
    for run in _runs(n=2):
        ent, truth = entities_and_truth(run)
        for e in ent.values():
            assert not (forbidden & set(e.keys())), f"leaked field in entity: {forbidden & set(e.keys())}"
        assert all("label" in t for t in truth.values())


def test_dataset_reproducible():
    a = dataset(5, seed=0)
    b = dataset(5, seed=0)
    for x, y in zip(a, b):
        assert np.array_equal(x, y)


def test_label_shuffle_is_chance():
    X, y, w, f = dataset(10, seed=0)
    Xtr, ytr, Xte, yte = split_by_world(X, y, w, seed=0)
    aucs = []
    for s in range(8):
        ysh = ytr.copy()
        np.random.RandomState(s).shuffle(ysh)
        aucs.append(roc_auc_score(yte, fit_score(Xtr, ysh, Xte)))
    assert np.mean(aucs) < 0.70


def test_no_single_feature_separates_perfectly():
    X, y, w, f = dataset(10, seed=0)
    for j, name in enumerate(FEATURES_NAMES):
        col = X[:, j]
        if len(set(col.tolist())) < 2:
            continue
        auc = roc_auc_score(y, col)
        assert max(auc, 1 - auc) < 0.98, f"{name} alone separates ({auc:.3f}) -> leak / too-easy"
