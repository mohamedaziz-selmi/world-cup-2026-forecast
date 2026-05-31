"""48-team World Cup Monte Carlo simulator (2026 format, official draw + bracket).

Pipeline: current Elo ratings -> Elo-driven Poisson scorelines -> the real 2026
tournament, simulated many times to estimate each team's probability of winning
the cup, reaching the final, and reaching the semis.

Modelling notes:
  - Match model: Elo-driven Poisson (walk-forward RPS 0.174, ~ties the Elo
    baseline). A time-decayed Dixon-Coles model was tested (calibrate.py) and did
    NOT beat it (0.177), so it is deliberately not used.
  - Host advantage: USA / Mexico / Canada get +75 Elo in their matches.
  - Knockout: FIFA's official Round-of-32 slotting (see bracket.py / Annex C).
    Each simulation plays the groups, then fills the real bracket from the
    standings — including the best-thirds-to-slot assignment — through to the
    final. Not a random draw.
  - Live: played matches are pulled from openfootball (public domain, no key) and
    used as-is; only unplayed matches are simulated. Dormant until kickoff
    (2026-06-11), then the forecast conditions on reality automatically.
"""
from collections import Counter
from pathlib import Path

import numpy as np
import pandas as pd

import bracket
import live
from draw_2026 import OFFICIAL_GROUPS
from elo import expected_home, run_elo
from match_model import EloPoisson

RAW = Path(__file__).resolve().parents[1] / "data" / "raw"
PROC = Path(__file__).resolve().parents[1] / "data" / "processed"
N_SIMS = 20000
RNG = np.random.default_rng(42)
HOSTS = {"United States", "Mexico", "Canada"}
HOST_BONUS = 75.0   # Elo points: the three hosts play in their own countries


def eff(team, ratings):
    return ratings[team] + (HOST_BONUS if team in HOSTS else 0.0)


def load_rate_fit():
    df = pd.read_csv(RAW / "results.csv", parse_dates=["date"])
    df = (df.dropna(subset=["home_score", "away_score"])
            .sort_values("date").reset_index(drop=True))
    df, ratings = run_elo(df)
    model = EloPoisson().fit(df["elo_diff"], df["home_score"], df["away_score"])
    return df, ratings, model


def official_groups(ratings):
    missing = [t for teams in OFFICIAL_GROUPS.values() for t in teams
               if t not in ratings]
    if missing:
        raise SystemExit(f"No Elo rating for: {missing}\n"
                         "Fix the spelling in draw_2026.py to match the dataset.")
    return {g: list(teams) for g, teams in OFFICIAL_GROUPS.items()}


def play_match(a, b, ratings, model, rng):
    lh, la = model.lam_neutral(eff(a, ratings), eff(b, ratings))
    return int(rng.poisson(lh)), int(rng.poisson(la))


def sim_group(teams, ratings, model, rng, results=None):
    pts = {t: 0 for t in teams}
    gd = {t: 0 for t in teams}
    gf = {t: 0 for t in teams}
    for i in range(4):
        for j in range(i + 1, 4):
            a, b = teams[i], teams[j]
            real = live.result_for(results, a, b) if results else None
            ga, gb = real if real else play_match(a, b, ratings, model, rng)
            gf[a] += ga; gf[b] += gb
            gd[a] += ga - gb; gd[b] += gb - ga
            if ga > gb:
                pts[a] += 3
            elif gb > ga:
                pts[b] += 3
            else:
                pts[a] += 1; pts[b] += 1
    ranked = sorted(teams, key=lambda t: (pts[t], gd[t], gf[t]), reverse=True)
    return ranked, pts, gd, gf


def play_knockout(a, b, ratings, model, rng):
    ga, gb = play_match(a, b, ratings, model, rng)
    if ga > gb:
        return a
    if gb > ga:
        return b
    return a if rng.random() < expected_home(eff(a, ratings) - eff(b, ratings)) else b


def simulate_once(groups, ratings, model, rng, results=None):
    winners, runners, thirds = {}, {}, []
    for g, teams in groups.items():
        ranked, pts, gd, gf = sim_group(teams, ratings, model, rng, results)
        winners[g] = ranked[0]
        runners[g] = ranked[1]
        t = ranked[2]
        thirds.append((t, g, pts[t], gd[t], gf[t]))
    thirds.sort(key=lambda x: (x[2], x[3], x[4]), reverse=True)
    top8 = [(t, g) for (t, g, _, _, _) in thirds[:8]]

    def play(a, b):
        return play_knockout(a, b, ratings, model, rng)

    return bracket.run_knockout(winners, runners, top8, play)


def main():
    df, ratings, model = load_rate_fit()
    groups = official_groups(ratings)

    known = {t for teams in groups.values() for t in teams}
    results = live.fetch_results(known)
    if results:
        print(f"live: incorporating {len(results)} finished match(es) from openfootball\n")
    else:
        print("live: 0 finished matches yet (kickoff 2026-06-11) — full simulation\n")

    champ, fin, sf = Counter(), Counter(), Counter()
    for _ in range(N_SIMS):
        c, finals, semis = simulate_once(groups, ratings, model, RNG, results)
        champ[c] += 1
        for t in finals:
            fin[t] += 1
        for t in semis:
            sf[t] += 1

    all_teams = [t for teams in groups.values() for t in teams]
    rows = [(t, round(ratings[t]), champ[t] / N_SIMS, fin[t] / N_SIMS, sf[t] / N_SIMS)
            for t in all_teams]
    res = (pd.DataFrame(rows, columns=["team", "elo", "p_champion", "p_final", "p_semi"])
             .sort_values("p_champion", ascending=False).reset_index(drop=True))
    PROC.mkdir(parents=True, exist_ok=True)
    res.to_csv(PROC / "sim_results.csv", index=False)

    print(f"OFFICIAL 2026 FIELD + BRACKET — {N_SIMS:,} simulations\n")
    print("Top 16 by P(win the cup):\n")
    print(f"{'team':<22}{'elo':>6}{'champ':>9}{'final':>8}{'semi':>8}")
    print("-" * 53)
    for _, x in res.head(16).iterrows():
        print(f"{x['team']:<22}{x['elo']:>6}{x['p_champion']*100:>8.1f}%"
              f"{x['p_final']*100:>7.1f}%{x['p_semi']*100:>7.1f}%")
    print(f"\nfull table -> {PROC / 'sim_results.csv'}")


if __name__ == "__main__":
    main()
