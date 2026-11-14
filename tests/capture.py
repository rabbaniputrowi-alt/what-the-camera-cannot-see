"""Open the page in headless Edge, exercise the controls and save screenshots. Used to check the page
before publishing and to retake captures after a data change.

Usage: uv run --with playwright python tests/capture.py [url] [outdir]
Needs Microsoft Edge installed (uses it through Playwright's msedge channel, no browser download).
"""
import json, sys
from pathlib import Path
from playwright.sync_api import sync_playwright

url = sys.argv[1] if len(sys.argv) > 1 else "http://127.0.0.1:8765/"
out = Path(sys.argv[2] if len(sys.argv) > 2 else "logs/capture")
out.mkdir(parents=True, exist_ok=True)
STATE = """() => ({
  tagA: document.getElementById('tag-a').textContent, tagB: document.getElementById('tag-b').textContent,
  live: document.getElementById('live').textContent,
  rows: [...document.querySelectorAll('#pairs tbody tr')].map(r => r.textContent),
  imgs: [document.getElementById('img-a').naturalWidth, document.getElementById('img-b').naturalWidth],
  hot: document.getElementById('hot-count').textContent,
  overlayInk: (() => { const c = document.getElementById('overlay'); const d = c.getContext('2d').getImageData(0, 0, c.width, c.height).data; let n = 0; for (let i = 3; i < d.length; i += 4) if (d[i]) n++; return n; })(),
})"""

with sync_playwright() as p:
    b = p.chromium.launch(channel="msedge", headless=True)
    page = b.new_page(viewport={"width": 1280, "height": 1500})
    errors = []
    page.on("console", lambda m: errors.append(m.text) if m.type == "error" else None)
    page.on("pageerror", lambda e: errors.append(str(e)))
    failed = []
    page.on("response", lambda r: failed.append(f"{r.status} {r.url}") if r.status >= 400 else None)
    page.goto(url, wait_until="networkidle")
    page.wait_for_timeout(1500)

    def shot(name, full=False):
        page.wait_for_timeout(1200)
        page.screenshot(path=str(out / f"{name}.png"), full_page=full)
        s = page.evaluate(STATE)
        print(f"\n[{name}] {s['tagA']} | {s['tagB']} | images {s['imgs']} | hotspots {s['hot']} | overlay pixels {s['overlayInk']}")
        print("  " + s["live"])
        return s

    s = shot("01_default", full=True)
    print("  table:"); [print("    " + r) for r in s["rows"]]
    page.check("#layer-rule"); page.check("#layer-hot"); shot("02_rule_hotspots")
    page.uncheck("#layer-rule"); page.uncheck("#layer-hot"); page.uncheck("#layer-change"); page.check("#layer-opt"); shot("03_optical")
    page.uncheck("#layer-opt"); page.check("#layer-change")
    page.click("#preset-placebo"); shot("04_placebo")
    page.click("#preset-fire"); page.click("#pick-pol button[data-pol=hh]"); shot("05_hh")
    page.click("#pick-pol button[data-pol=hv]")
    page.locator("#pick-track button").nth(0).click(); shot("06_other_track")
    page.locator("#pick-window button").nth(1).click(); shot("07_window2")
    page.locator("#pick-track button").nth(1).click(); s = shot("08_window2_t125")
    print("  table:"); [print("    " + r) for r in s["rows"]]
    page.evaluate("() => { const s = document.getElementById('slide'); s.value = 15; s.dispatchEvent(new Event('input')); }")
    shot("09_slider_left")
    page.set_viewport_size({"width": 390, "height": 800}); shot("10_phone", full=True)
    print("\nconsole errors:", errors or "none")
    print("failed requests:", failed or "none")
    b.close()
