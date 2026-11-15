"""Save the page's change overlays (window 1, track 125) as PNGs for the demo deck.

Usage: python -m http.server 8765 --directory docs   (in another shell)
       uv run --with playwright python tests/deck_overlays.py
Writes logs/deck/ov_*.png, which pipeline/build_deck.py reads.
"""
import base64
from pathlib import Path
from playwright.sync_api import sync_playwright

out = Path("logs/deck")
out.mkdir(parents=True, exist_ok=True)


def grab(page, name):
    data = page.evaluate("document.getElementById('overlay').toDataURL('image/png')")
    (out / name).write_bytes(base64.b64decode(data.split(",")[1]))


with sync_playwright() as p:
    b = p.chromium.launch(channel="msedge", headless=True)
    pg = b.new_page(viewport={"width": 1920, "height": 1080})
    pg.goto("http://127.0.0.1:8765/", wait_until="networkidle")
    pg.wait_for_timeout(4000)
    pg.click("#preset-fire"); pg.wait_for_timeout(1500); grab(pg, "ov_change_fire.png")
    pg.uncheck("#layer-change"); pg.check("#layer-rule"); pg.wait_for_timeout(1000); grab(pg, "ov_rule_fire.png")
    pg.uncheck("#layer-rule"); pg.check("#layer-opt"); pg.wait_for_timeout(1000); grab(pg, "ov_opt.png")
    pg.uncheck("#layer-opt"); pg.check("#layer-change"); pg.click("#preset-placebo"); pg.wait_for_timeout(1500)
    grab(pg, "ov_change_placebo.png")
    pg.screenshot(path=str(out / "app_default.png"))
    b.close()
