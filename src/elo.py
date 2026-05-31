"""World-Football-style Elo engine for international matches.

Ratings are computed ONLINE: each match is rated using only the ratings that
existed before kickoff, then both teams update from the result. That means the
pre-match Elo of any match never sees its own outcome or any future match —
no leakage when these ratings are used as model features later.

Method follows the World Football Elo convention:
  - home advantage added only for non-neutral venues
  - K-factor scaled by tournament importance
  - goal-difference multiplier so blowouts move ratings more
"""
from __future__ import annotations

import pandas as pd

HOME_ADVANTAGE = 100.0   # Elo points for the home side at a non-neutral venue
BASE_RATING = 1500.0     # every team's starting rating


def k_for_tournament(t: str) -> float:
    """Importance weight. Bigger competition => result moves ratings more."""
    t = (t or "").lower()
    if "friendly" in t:
        return 20.0
    if t == "fifa world cup":
        return 60.0
    if "world cup" in t and "qual" in t:
        return 40.0
    if "world cup" in t:                       # finals-adjacent (e.g. play-offs)
        return 55.0
    if "confederations" in t:
        return 45.0
    if any(k in t for k in ("uefa euro", "copa am", "african cup of nations",
                            "afc asian cup", "gold cup")):
        return 40.0 if "qual" in t else 50.0
    if "nations league" in t:
        return 40.0
    if "qual" in t:
        return 40.0
    return 30.0


def goal_diff_multiplier(gd: int) -> float:
    gd = abs(int(gd))
    if gd <= 1:
        return 1.0
    if gd == 2:
        return 1.5
    return (11 + gd) / 8.0


def expected_home(rating_diff: float) -> float:
    return 1.0 / (1.0 + 10.0 ** (-rating_diff / 400.0))


def run_elo(matches: pd.DataFrame) -> pd.DataFrame:
    """Add pre-match Elo features to a chronologically-sorted match frame.

    Required columns: home_team, away_team, home_score, away_score,
    tournament, neutral. Returns a copy with:
      elo_home_pre, elo_away_pre, elo_diff (incl. home adv), outcome
      (outcome: 0 = away win, 1 = draw, 2 = home win).
    """
    ratings: dict[str, float] = {}
    eh, ea, ediff, out = [], [], [], []

    for r in matches.itertuples(index=False):
        rh = ratings.get(r.home_team, BASE_RATING)
        ra = ratings.get(r.away_team, BASE_RATING)
        adv = 0.0 if bool(r.neutral) else HOME_ADVANTAGE
        diff = rh - ra + adv

        if r.home_score > r.away_score:
            score_home, result = 1.0, 2
        elif r.home_score == r.away_score:
            score_home, result = 0.5, 1
        else:
            score_home, result = 0.0, 0

        k = k_for_tournament(r.tournament) * goal_diff_multiplier(r.home_score - r.away_score)
        change = k * (score_home - expected_home(diff))
        ratings[r.home_team] = rh + change
        ratings[r.away_team] = ra - change

        eh.append(rh); ea.append(ra); ediff.append(diff); out.append(result)

    res = matches.copy()
    res["elo_home_pre"] = eh
    res["elo_away_pre"] = ea
    res["elo_diff"] = ediff
    res["outcome"] = out
    return res, ratings
