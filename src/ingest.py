"""Download the canonical international football dataset.

martj42/international_results — every men's full international from 1872 to today
(~48k matches: World Cups, qualifiers, continental tournaments, friendlies).
Direct CSV download, no scraping, no auth.
"""
from pathlib import Path
import urllib.request

RAW = Path(__file__).resolve().parents[1] / "data" / "raw"
BASE = "https://raw.githubusercontent.com/martj42/international_results/master/"
FILES = ["results.csv", "goalscorers.csv", "shootouts.csv"]


def main() -> None:
    RAW.mkdir(parents=True, exist_ok=True)
    for f in FILES:
        dest = RAW / f
        print(f"downloading {f} ...")
        urllib.request.urlretrieve(BASE + f, dest)
        print(f"  -> {dest}  ({dest.stat().st_size / 1e6:.1f} MB)")
    print("done.")


if __name__ == "__main__":
    main()
