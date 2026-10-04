from __future__ import annotations
import numpy as np
from sklearn.linear_model import LogisticRegression
from sklearn.ensemble import IsolationForest

from features import build_features
from gates import run_gates
from analyzer import run_analyzer


class Learner:
    def __init__(self):
        self.clf = None
        self.iso = None

    def train(self, X, y):
        X = np.array(X, dtype=float)
        y = np.array(y)
        self.clf = LogisticRegression(max_iter=1000, class_weight="balanced")
        self.clf.fit(X, y)
        self.iso = IsolationForest(contamination="auto", random_state=0)
        self.iso.fit(X[y == 0] if (y == 0).any() else X)

    def predict(self, X):
        if self.clf is None:
            return np.zeros(len(X))
        return self.clf.predict_proba(np.array(X, dtype=float))[:, 1]

    def anomaly(self, X):
        if self.iso is None:
            return np.zeros(len(X))
        return -self.iso.score_samples(np.array(X, dtype=float))


def detect(entities, learner=None, thresh=0.5):
    flagged = {f.entity for f in run_gates(entities)}
    flagged |= {f.entity for f in run_analyzer(entities)}
    if learner is not None and learner.clf is not None:
        feats = build_features(entities)
        ids = list(feats.keys())
        probs = learner.predict([feats[i] for i in ids])
        for i, p in zip(ids, probs):
            if p >= thresh:
                flagged.add(i)
    return flagged
