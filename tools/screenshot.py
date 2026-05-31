"""Capture a full-page PNG of report.html for the README preview.

Uses headless Chrome via Selenium (Selenium Manager auto-fetches the driver).
Output: docs/preview.png
"""
import time
from pathlib import Path

from selenium import webdriver
from selenium.webdriver.chrome.options import Options

ROOT = Path(__file__).resolve().parents[1]
URL = (ROOT / "report.html").as_uri()
OUT = ROOT / "docs" / "preview.png"


def main():
    OUT.parent.mkdir(exist_ok=True)
    opts = Options()
    opts.add_argument("--headless=new")
    opts.add_argument("--hide-scrollbars")
    opts.add_argument("--force-device-scale-factor=2")
    opts.add_argument("--window-size=1240,1400")
    driver = webdriver.Chrome(options=opts)
    try:
        driver.get(URL)
        time.sleep(3)                       # let web fonts load
        height = driver.execute_script("return document.body.scrollHeight")
        driver.set_window_size(1240, height + 40)
        time.sleep(1)
        driver.save_screenshot(str(OUT))
    finally:
        driver.quit()
    print(f"saved {OUT} ({OUT.stat().st_size/1024:.0f} KB)")


if __name__ == "__main__":
    main()
