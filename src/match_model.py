"""Elo-driven Poisson scoreline model.

Turns a pre-match Elo difference into expected goals for each side, then treats
goals as independent Poisson. This yields full scoreline probabilities, which
the tournament simulator needs for group-stage tiebreakers (goal difference and
goals scored). The coefficients are LEARNED from the data via Poisson
regression, not assigned by hand.

This is the pragmatic first match model. A fitted team-level attack/defense
Poisson (Dixon-Coles, with its low-score correction) is the planned upgrade;
this keeps the end-to-end pipeline moving and is measured against the same RPS
yardstick as everything else.
"""
from __future__ import annotations

import math

import numpy as np
from scipy.stats import poisson
from sklearn.linear_model import PoissonRegressor

MAX_GOALS = 10


class EloPoisson:
    def __init__(self) -> None:
        self.home = PoissonRegressor(alpha=1e-6, max_iter=2000)
        self.away = PoissonRegressor(alpha=1e-6, max_iter=2000)

    def fit(self, elo_diff, home_goals, away_goals) -> "EloPoisson":
        X = (np.asarray(elo_diff, dtype=float) / 100.0).reshape(-1, 1)
        self.home.fit(X, np.asarray(home_goals, dtype=float))
        self.away.fit(X, np.asarray(away_goals, dtype=float))
        # cache scalar coefficients for fast simulation
        self.h_int, self.h_co = float(self.home.intercept_), float(self.home.coef_[0])
        self.a_int, self.a_co = float(self.away.intercept_), float(self.away.coef_[0])
        return self

    def lambdas(self, elo_diff):
        X = (np.asarray(elo_diff, dtype=float) / 100.0).reshape(-1, 1)
        return self.home.predict(X), self.away.predict(X)

    def lam_neutral(self, ra: float, rb: float):
        """Symmetric expected goals for a NEUTRAL match (no home/away bias).

        Drops the home-vs-away intercept gap and keeps only the rating-driven
        supremacy, so two equal teams get identical expected goals (no
        dependence on which side we list first).
        """
        base = (self.h_int + self.a_int) / 2.0
        slope = (self.h_co - self.a_co) / 2.0
        d = (ra - rb) / 100.0
        return math.exp(base + slope * d), math.exp(base - slope * d)

    def outcome_probs(self, elo_diff):
        """(n,3) array of [away, draw, home] win probs for home/away matches."""
        lh, la = self.lambdas(elo_diff)
        ks = np.arange(MAX_GOALS + 1)
        out = np.zeros((len(lh), 3))
        for i in range(len(lh)):
            # M[h, a] = P(home scores h) * P(away scores a)
            M = np.outer(poisson.pmf(ks, lh[i]), poisson.pmf(ks, la[i]))
            out[i, 2] = np.tril(M, -1).sum()  # home win: h > a (below diagonal)
            out[i, 1] = np.trace(M)           # draw:     h = a
            out[i, 0] = np.triu(M, 1).sum()   # away win: a > h (above diagonal)
            out[i] /= out[i].sum()            # renormalise truncated tail
        return out
