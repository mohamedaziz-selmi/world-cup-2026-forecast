"""Dixon-Coles-style team-strength match model with time decay.

Each team gets a learned ATTACK and DEFENSE coefficient; goals are Poisson with
  log E[home goals] = intercept + attack[home] + defense[away] + gamma*(home)
  log E[away goals] = intercept + attack[away] + defense[home]
Recent matches are weighted more (exponential time decay, configurable
half-life), and the Dixon-Coles low-score correction (rho) nudges up the
probability of 0-0 / 1-0 / 0-1 / 1-1 results that an independent Poisson
underestimates.

Coefficients are fit by weighted Poisson regression — fast and stable — rather
than hand-set. `asof` controls "today" for the decay, which makes honest
walk-forward backtesting possible (fit as-of the start of each test year).
"""
from __future__ import annotations

import math

import numpy as np
import pandas as pd
from scipy.sparse import csr_matrix, hstack
from scipy.stats import poisson
from sklearn.linear_model import PoissonRegressor
from sklearn.preprocessing import OneHotEncoder

MAX_GOALS = 10


class DixonColes:
    def __init__(self, half_life_years: float = 2.0, alpha: float = 1e-3,
                 rho: float = -0.05) -> None:
        self.half_life_years = half_life_years
        self.alpha = alpha
        self.rho = rho

    def fit(self, df: pd.DataFrame, asof=None) -> "DixonColes":
        asof = pd.Timestamp(asof) if asof is not None else df["date"].max()
        df = df[df["date"] <= asof]

        xi = math.log(2) / self.half_life_years
        age = (asof - df["date"]).dt.days.to_numpy() / 365.25
        w = np.exp(-xi * age)

        home = df["home_team"].to_numpy()
        away = df["away_team"].to_numpy()
        neutral = df["neutral"].astype(bool).to_numpy()
        n = len(df)

        # long format: row per (attacking team, defending team)
        att = np.concatenate([home, away])
        dfn = np.concatenate([away, home])
        is_home = np.concatenate([(~neutral).astype(float), np.zeros(n)])
        y = np.concatenate([df["home_score"].to_numpy(),
                            df["away_score"].to_numpy()]).astype(float)
        sw = np.concatenate([w, w])

        self.enc_att = OneHotEncoder(handle_unknown="ignore", sparse_output=True)
        self.enc_def = OneHotEncoder(handle_unknown="ignore", sparse_output=True)
        Xa = self.enc_att.fit_transform(att.reshape(-1, 1))
        Xd = self.enc_def.fit_transform(dfn.reshape(-1, 1))
        X = hstack([Xa, Xd, csr_matrix(is_home.reshape(-1, 1))]).tocsr()

        self.model = PoissonRegressor(alpha=self.alpha, max_iter=3000)
        self.model.fit(X, y, sample_weight=sw)

        coef = self.model.coef_
        na = Xa.shape[1]
        self.intercept = float(self.model.intercept_)
        self.gamma = float(coef[-1])
        self.attack = {t: float(coef[i])
                       for i, t in enumerate(self.enc_att.categories_[0])}
        self.defense = {t: float(coef[na + i])
                        for i, t in enumerate(self.enc_def.categories_[0])}
        return self

    def _lam(self, at: str, dt: str, home: bool = False) -> float:
        return math.exp(self.intercept + self.attack.get(at, 0.0)
                        + self.defense.get(dt, 0.0)
                        + (self.gamma if home else 0.0))

    def match_lambdas(self, home, away, neutral):
        return self._lam(home, away, home=not neutral), self._lam(away, home)

    def neutral_lambdas(self, a, b, host_a=False, host_b=False):
        return self._lam(a, b, home=host_a), self._lam(b, a, home=host_b)

    def _corrected_matrix(self, lam, mu):
        ks = np.arange(MAX_GOALS + 1)
        M = np.outer(poisson.pmf(ks, lam), poisson.pmf(ks, mu))   # M[home, away]
        r = self.rho
        M[0, 0] *= 1 - lam * mu * r
        M[0, 1] *= 1 + lam * r
        M[1, 0] *= 1 + mu * r
        M[1, 1] *= 1 - r
        np.clip(M, 0, None, out=M)
        return M / M.sum()

    def outcome_probs(self, df):
        """(n,3) [away, draw, home] win probs with the DC low-score correction."""
        out = np.zeros((len(df), 3))
        homes = df["home_team"].to_numpy()
        aways = df["away_team"].to_numpy()
        neutral = df["neutral"].astype(bool).to_numpy()
        for i in range(len(df)):
            lam, mu = self.match_lambdas(homes[i], aways[i], neutral[i])
            M = self._corrected_matrix(lam, mu)
            out[i, 2] = np.tril(M, -1).sum()   # home win (home goals > away)
            out[i, 1] = np.trace(M)            # draw
            out[i, 0] = np.triu(M, 1).sum()    # away win
        return out

    def sample_score(self, a, b, rng, host_a=False, host_b=False):
        """Sample a scoreline (a_goals, b_goals) from the DC-corrected joint."""
        lam, mu = self.neutral_lambdas(a, b, host_a, host_b)
        M = self._corrected_matrix(lam, mu)              # M[a_goals, b_goals]
        flat = rng.choice(M.size, p=M.ravel())
        return divmod(flat, M.shape[1])
