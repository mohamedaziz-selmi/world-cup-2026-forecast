"""Render a static forecast page (report.html) from the simulation output.

The numbers are baked in (open the file directly, no server needed). Editorial
dark theme; Fraunces for display, IBM Plex Mono for the figures.
"""
from datetime import date
from pathlib import Path

import pandas as pd

from draw_2026 import OFFICIAL_GROUPS

ROOT = Path(__file__).resolve().parents[1]
PROC = ROOT / "data" / "processed"
OUT = ROOT / "report.html"

STYLE = """<style>
:root{
  --ink: oklch(0.17 0.02 264); --ink2: oklch(0.21 0.022 264);
  --line: oklch(0.32 0.02 264); --text: oklch(0.95 0.01 250);
  --muted: oklch(0.68 0.02 255); --gold: oklch(0.82 0.13 85);
  --c1: oklch(0.60 0.13 205); --c2: oklch(0.80 0.15 152);
}
*{box-sizing:border-box;margin:0;padding:0}
body{background:var(--ink);color:var(--text);font-family:"IBM Plex Mono",ui-monospace,monospace;
 line-height:1.5;-webkit-font-smoothing:antialiased;
 background-image:radial-gradient(120% 80% at 82% -12%, oklch(0.28 0.06 264 / .6), transparent 58%);}
main{max-width:920px;margin:0 auto;padding:clamp(28px,6vw,80px) clamp(20px,5vw,48px) 80px}
.kicker{font-size:12px;letter-spacing:.22em;text-transform:uppercase;color:var(--muted)}
h1{font-family:"Fraunces",serif;font-weight:900;font-size:clamp(46px,9vw,98px);line-height:.92;
 letter-spacing:-.025em;margin:.16em 0 .12em}
.dek{color:var(--muted);max-width:64ch;font-size:14px}
header{border-bottom:1px solid var(--line);padding-bottom:28px;margin-bottom:44px}
h2{font-family:"Fraunces",serif;font-weight:600;font-size:22px;margin:0 0 18px}
section{margin-bottom:56px}
.list{list-style:none}
.row{display:grid;grid-template-columns:34px 1fr 1.5fr auto;gap:16px;align-items:center;
 padding:15px 0;border-bottom:1px solid oklch(0.32 0.02 264 / .5)}
.rank{color:var(--muted);font-size:13px;font-variant-numeric:tabular-nums}
.team{font-family:"Fraunces",serif;font-size:20px;font-weight:600}
.bar{height:7px;border-radius:99px;background:oklch(0.32 0.02 264 / .5);overflow:hidden}
.fill{display:block;height:100%;border-radius:99px;background:linear-gradient(90deg,var(--c1),var(--c2))}
.pc{font-weight:600;font-variant-numeric:tabular-nums;text-align:right;min-width:62px}
.sub{grid-column:2 / -1;color:var(--muted);font-size:12px;margin-top:-7px}
.row.lead .team,.row.lead .pc{color:var(--gold)}
.row.lead .fill{background:linear-gradient(90deg,oklch(0.70 0.12 96),var(--gold))}
.grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(180px,1fr));gap:14px}
.card{background:var(--ink2);border:1px solid var(--line);border-radius:12px;padding:14px 16px}
.card h3{font-family:"Fraunces",serif;font-size:15px;color:var(--muted);margin-bottom:8px;letter-spacing:.05em}
.card ul{list-style:none}
.card li{display:flex;justify-content:space-between;gap:8px;padding:5px 0;font-size:13px;
 border-top:1px solid oklch(0.32 0.02 264 / .35)}
.card li:first-child{border-top:0}
.gp{color:var(--muted);font-variant-numeric:tabular-nums}
.stats{display:flex;gap:clamp(20px,5vw,44px);flex-wrap:wrap;margin-top:26px}
.stat b{display:block;font-family:"Fraunces",serif;font-size:30px;font-weight:900;line-height:1;
 background:linear-gradient(90deg,var(--text),var(--c2));-webkit-background-clip:text;
 background-clip:text;color:transparent}
.stat span{font-size:11px;letter-spacing:.16em;text-transform:uppercase;color:var(--muted)}
footer{border-top:1px solid var(--line);padding-top:24px;color:var(--muted);font-size:12px;line-height:1.75}
footer b{color:var(--text);font-weight:600}
</style>"""


def pct(x):
    return f"{x * 100:.1f}%"


def main():
    res = pd.read_csv(PROC / "sim_results.csv")
    by_team = dict(zip(res.team, res.p_champion))
    top = res.head(12).reset_index(drop=True)
    maxp = float(res.p_champion.max())

    rows = []
    for i, r in top.iterrows():
        rank = i + 1
        w = max(2.0, r.p_champion / maxp * 100)
        lead = " lead" if rank == 1 else ""
        rows.append(
            f'<li class="row{lead}"><span class="rank">{rank:02d}</span>'
            f'<span class="team">{r.team}</span>'
            f'<span class="bar"><span class="fill" style="width:{w:.1f}%"></span></span>'
            f'<span class="pc">{pct(r.p_champion)}</span>'
            f'<span class="sub">final {pct(r.p_final)} · semis {pct(r.p_semi)}</span></li>')
    contenders = "".join(rows)

    cards = []
    for g, teams in OFFICIAL_GROUPS.items():
        items = "".join(
            f'<li><span>{t}</span><span class="gp">{pct(by_team.get(t, 0.0))}</span></li>'
            for t in teams)
        cards.append(f'<div class="card"><h3>Group {g}</h3><ul>{items}</ul></div>')
    groups = "".join(cards)

    today = date.today().strftime("%B %d, %Y").replace(" 0", " ")

    html = (
        "<!doctype html><html lang='en'><head><meta charset='utf-8'>"
        "<meta name='viewport' content='width=device-width,initial-scale=1'>"
        "<title>World Cup 2026 — Title Race</title>"
        "<link rel='preconnect' href='https://fonts.googleapis.com'>"
        "<link rel='preconnect' href='https://fonts.gstatic.com' crossorigin>"
        "<link href='https://fonts.googleapis.com/css2?family=Fraunces:opsz,wght@9..144,400;"
        "9..144,600;9..144,900&family=IBM+Plex+Mono:wght@400;500;600&display=swap' rel='stylesheet'>"
        + STYLE +
        "</head><body><main>"
        "<header>"
        "<div class='kicker'>FIFA World Cup 2026 · Canada · Mexico · USA</div>"
        "<h1>Title Race</h1>"
        f"<p class='dek'>Win probabilities from 20,000 Monte Carlo simulations of the full "
        f"48-team tournament, played through FIFA's official bracket. Match model "
        f"walk-forward RPS 0.174. Generated {today}.</p>"
        "<div class='stats'>"
        "<div class='stat'><b>48</b><span>teams</span></div>"
        "<div class='stat'><b>104</b><span>matches</span></div>"
        "<div class='stat'><b>20k</b><span>simulations</span></div>"
        "<div class='stat'><b>0.174</b><span>RPS · walk-forward</span></div>"
        "</div>"
        "</header>"
        f"<section><h2>Contenders</h2><ol class='list'>{contenders}</ol></section>"
        f"<section><h2>The Field</h2><div class='grid'>{groups}</div></section>"
        "<footer>"
        "<b>Method.</b> Online Elo ratings (all ~49k men's internationals since 1872) → "
        "Elo-driven Poisson scorelines → Monte Carlo over the official 2026 draw. "
        "Hosts get +75 Elo at home. The knockout uses FIFA's official Round-of-32 "
        "slotting (Annex C), resolved from each simulation's group standings. A "
        "Dixon-Coles model was tested and did not beat this, so it isn't used.<br>"
        "<b>Caveat.</b> Football is genuinely random; these are probabilities, not "
        "predictions, and not betting advice. Data: martj42/international_results."
        "</footer></main></body></html>")

    OUT.write_text(html, encoding="utf-8")
    docs = ROOT / "docs"
    docs.mkdir(exist_ok=True)
    (docs / "index.html").write_text(html, encoding="utf-8")   # for GitHub Pages
    print(f"wrote {OUT} and {docs / 'index.html'}")


if __name__ == "__main__":
    main()
