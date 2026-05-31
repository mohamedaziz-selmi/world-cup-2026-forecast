"""Backtest: does the Elo model actually beat a dumb baseline?

This is the most important file in the project. Before we add a single fancy
feature, we prove the core works and we set up the yardstick everything else is
measured against.

Metric: Ranked Probability Score (RPS) — the standard for ordered 3-outcome
football forecasts (away / draw / home). Lower is better. We also report
multiclass log-loss and plain accuracy for context.

No leakage:
  - Elo ratings are online (pre-match only).
  - The Elo -> outcome probability mapping is fit on a TRAIN period and scored
    on a strictly later TEST period.
"""
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import accuracy_score, log_loss

from elo import run_elo
from match_model import EloPoisson

RAW = Path(__file__).resolve().parents[1] / "data" / "raw"
SPLIT = "2014-01-01"   # fit on everything before, evaluate on everything after


def rps(probs: np.ndarray, outcomes: np.ndarray) -> float:
    """Ranked Probability Score for ordered outcomes [away, draw, home]."""
    cum_p = np.cumsum(probs, axis=1)
    onehot = np.zeros_like(probs)
    onehot[np.arange(len(outcomes)), outcomes] = 1.0
    cum_o = np.cumsum(onehot, axis=1)
    return float(np.mean(np.sum((cum_p - cum_o) ** 2, axis=1) / (probs.shape[1] - 1)))


def main() -> None:
    df = pd.read_csv(RAW / "results.csv", parse_dates=["date"])
    df = (df.dropna(subset=["home_score", "away_score"])
            .sort_values("date")
            .reset_index(drop=True))
    df, _ = run_elo(df)

    train = df[df["date"] < SPLIT]
    test = df[df["date"] >= SPLIT]

    # scale elo_diff for stable logistic fitting
    Xtr = (train[["elo_diff"]].values) / 100.0
    Xte = (test[["elo_diff"]].values) / 100.0
    ytr = train["outcome"].values
    yte = test["outcome"].values

    # --- Model: multinomial logit, elo_diff -> P(away, draw, home)
    clf = LogisticRegression(max_iter=2000)
    clf.fit(Xtr, ytr)
    order = np.argsort(clf.classes_)             # force column order 0,1,2
    p_elo = clf.predict_proba(Xte)[:, order]

    # --- Model: Elo-driven Poisson scoreline model -> outcome probs
    ep = EloPoisson().fit(train["elo_diff"], train["home_score"], train["away_score"])
    p_pois = ep.outcome_probs(test["elo_diff"].values)

    # --- Baseline: train-set base rates, identical for every match
    base = np.array([(ytr == c).mean() for c in (0, 1, 2)])
    p_base = np.tile(base, (len(yte), 1))

    print(f"matches:  train={len(train):,}   test={len(test):,}")
    print(f"base rates  away/draw/home = {base.round(3)}\n")
    print(f"{'model':>10}   {'RPS':>7}  {'logloss':>8}  {'acc':>6}")
    print("-" * 38)
    for name, p in (("base-rate", p_base), ("elo", p_elo), ("elo-poisson", p_pois)):
        print(f"{name:>10}   {rps(p, yte):7.4f}  "
              f"{log_loss(yte, p, labels=[0, 1, 2]):8.4f}  "
              f"{accuracy_score(yte, p.argmax(1)):6.3f}")


if __name__ == "__main__":
    main()
