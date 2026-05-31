"""Rigorous walk-forward comparison of every match model.

For each test year (2014..latest) we refit on everything before it and predict
that year, then pool all out-of-sample predictions. This is the fair yardstick:
the time-decayed Dixon-Coles model is judged the same way as online Elo, so the
comparison is apples-to-apples (no model gets to peek at the future, none is
unfairly penalised for being static).
"""
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import accuracy_score, log_loss

from dc_model import DixonColes
from elo import run_elo
from match_model import EloPoisson

RAW = Path(__file__).resolve().parents[1] / "data" / "raw"
START = 2014


def rps(probs, outcomes):
    cum_p = np.cumsum(probs, axis=1)
    onehot = np.zeros_like(probs)
    onehot[np.arange(len(outcomes)), outcomes] = 1.0
    cum_o = np.cumsum(onehot, axis=1)
    return float(np.mean(np.sum((cum_p - cum_o) ** 2, axis=1) / (probs.shape[1] - 1)))


def main():
    df = pd.read_csv(RAW / "results.csv", parse_dates=["date"])
    df = (df.dropna(subset=["home_score", "away_score"])
            .sort_values("date").reset_index(drop=True))
    df, _ = run_elo(df)                      # online elo_diff + outcome columns
    ymax = int(df["date"].dt.year.max())

    models = ["base", "elo", "elo-poisson", "dc"]
    preds = {m: [] for m in models}
    outs = []

    for yr in range(START, ymax + 1):
        tr = df[df["date"] < f"{yr}-01-01"]
        te = df[(df["date"] >= f"{yr}-01-01") & (df["date"] < f"{yr + 1}-01-01")]
        if len(te) == 0 or len(tr) < 2000:
            continue
        outs.append(te["outcome"].to_numpy())

        base = np.array([(tr["outcome"] == c).mean() for c in (0, 1, 2)])
        preds["base"].append(np.tile(base, (len(te), 1)))

        clf = LogisticRegression(max_iter=2000).fit(
            tr[["elo_diff"]].to_numpy() / 100.0, tr["outcome"])
        order = np.argsort(clf.classes_)
        preds["elo"].append(
            clf.predict_proba(te[["elo_diff"]].to_numpy() / 100.0)[:, order])

        ep = EloPoisson().fit(tr["elo_diff"], tr["home_score"], tr["away_score"])
        preds["elo-poisson"].append(ep.outcome_probs(te["elo_diff"].to_numpy()))

        dc = DixonColes().fit(tr, asof=f"{yr}-01-01")
        preds["dc"].append(dc.outcome_probs(te))
        print(f"  ...{yr} done ({len(te)} matches)")

    O = np.concatenate(outs)
    print(f"\nwalk-forward {START}-{ymax}   pooled out-of-sample matches: {len(O):,}\n")
    print(f"{'model':>12}   {'RPS':>7}  {'logloss':>8}  {'acc':>6}")
    print("-" * 40)
    for m in models:
        P = np.vstack(preds[m])
        print(f"{m:>12}   {rps(P, O):7.4f}  "
              f"{log_loss(O, P, labels=[0, 1, 2]):8.4f}  "
              f"{accuracy_score(O, P.argmax(1)):6.3f}")


if __name__ == "__main__":
    main()
