"""Live data layer.

Two sources:
  1. openfootball/worldcup.json — PUBLIC DOMAIN, no key, no signup. The real 2026
     schedule + results as they are played. This powers between-match
     re-simulation (`fetch_results`). Free and always available.
  2. API-Football (api-sports.io) — used for injuries/standings, BUT verified
     that its FREE plan has NO access to season 2026 ("try from 2022 to 2024").
     So the functions below need a PAID plan to return 2026 data; they stay here
     ready for if/when a paid key is added. Header: x-apisports-key.

Run `python src/live.py` for the API-Football diagnostic (plan + quota + access).
"""
from __future__ import annotations

import os
from pathlib import Path

API_BASE = "https://v3.football.api-sports.io"
WC_LEAGUE = 1
WC_SEASON = 2026


def _load_env() -> None:
    env = Path(__file__).resolve().parents[1] / ".env"
    if env.exists():
        for line in env.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, v = line.split("=", 1)
                os.environ.setdefault(k.strip(), v.strip())


def get_key():
    _load_env()
    return os.environ.get("API_FOOTBALL_KEY") or None


def available() -> bool:
    return bool(get_key())


def _raw(path, **params):
    key = get_key()
    if not key:
        raise RuntimeError("No API_FOOTBALL_KEY in .env")
    import requests
    r = requests.get(f"{API_BASE}/{path}", headers={"x-apisports-key": key},
                     params=params, timeout=25)
    r.raise_for_status()
    return r.json()


def _get(path, **params):
    return _raw(path, **params).get("response", [])


def status():
    return _raw("status")


def get_teams():
    return _get("teams", league=WC_LEAGUE, season=WC_SEASON)


def get_standings():
    return _get("standings", league=WC_LEAGUE, season=WC_SEASON)


def get_injuries():
    return _get("injuries", league=WC_LEAGUE, season=WC_SEASON)


def get_fixtures():
    return _get("fixtures", league=WC_LEAGUE, season=WC_SEASON)


# --- Free results source: openfootball/worldcup.json (no key) -----------------

OPENFOOTBALL_URL = ("https://raw.githubusercontent.com/openfootball/"
                    "worldcup.json/master/2026/worldcup.json")
# openfootball spellings -> our dataset / draw_2026 spellings
NAME_FIX = {"USA": "United States", "Bosnia & Herzegovina": "Bosnia and Herzegovina"}


def _fix(name):
    return NAME_FIX.get(name, name)


def fetch_results(known_teams):
    """Finished real matches from openfootball (public domain, no key).

    Returns {(home, away): (gh, ga)} in dataset names, only for matches between
    two known teams that already have a score — so unresolved knockout slots like
    '1A' / 'W73' / '3A/B/C/D/F' are skipped automatically. Empty pre-tournament.
    """
    import json
    import urllib.request
    try:
        data = json.load(urllib.request.urlopen(OPENFOOTBALL_URL, timeout=25))
    except Exception:
        return {}
    out = {}
    for m in data.get("matches", []):
        t1, t2 = m.get("team1"), m.get("team2")
        s1, s2 = m.get("score1"), m.get("score2")
        if not (isinstance(t1, str) and isinstance(t2, str)):
            continue
        a, b = _fix(t1), _fix(t2)
        if a in known_teams and b in known_teams and s1 is not None and s2 is not None:
            out[(a, b)] = (int(s1), int(s2))
    return out


def result_for(results, a, b):
    """Look up a played result for the pair (a, b) in either orientation."""
    if (a, b) in results:
        return results[(a, b)]
    if (b, a) in results:
        gb, ga = results[(b, a)]
        return ga, gb
    return None


def diagnose() -> None:
    st = status().get("response", {})
    sub = st.get("subscription", {}) if isinstance(st, dict) else {}
    req = st.get("requests", {}) if isinstance(st, dict) else {}
    print(f"plan: {sub.get('plan')} | active: {sub.get('active')} | ends: {sub.get('end')}")
    print(f"requests today: {req.get('current')}/{req.get('limit_day')}\n")

    probes = (
        ("leagues", dict(id=WC_LEAGUE, season=WC_SEASON)),
        ("teams", dict(league=WC_LEAGUE, season=WC_SEASON)),
        ("standings", dict(league=WC_LEAGUE, season=WC_SEASON)),
        ("fixtures", dict(league=WC_LEAGUE, season=WC_SEASON)),
        ("injuries", dict(league=WC_LEAGUE, season=WC_SEASON)),
    )
    for path, params in probes:
        try:
            j = _raw(path, **params)
            print(f"[{path}] results={j.get('results')} errors={j.get('errors')}")
            resp = j.get("response", [])
            if path == "leagues" and resp:
                cov = resp[0].get("seasons", [{}])[-1].get("coverage")
                print(f"   coverage: {cov}")
            if path == "teams" and resp:
                print(f"   sample: {[t['team']['name'] for t in resp[:8]]}")
            if path == "fixtures" and resp:
                f0 = resp[0]
                print(f"   {len(resp)} fixtures; e.g. {f0['teams']['home']['name']} vs "
                      f"{f0['teams']['away']['name']} [{f0['fixture']['status']['short']}]")
            if path == "injuries":
                print(f"   {len(resp)} injury rows")
        except Exception as e:
            print(f"[{path}] ERROR {e!r}")


if __name__ == "__main__":
    diagnose()
