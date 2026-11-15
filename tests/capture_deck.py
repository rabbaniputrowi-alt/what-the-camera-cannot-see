"""Open the demo deck in headless Edge, capture every slide, and report errors, failed requests and banned glyphs.

Usage: uv run --with playwright python tests/capture_deck.py [url] [outdir]
"""
import sys
from pathlib import Path
from playwright.sync_api import sync_playwright

url = sys.argv[1] if len(sys.argv) > 1 else "http://127.0.0.1:8765/deck/"
out = Path(sys.argv[2] if len(sys.argv) > 2 else "logs/deck/capture")
out.mkdir(parents=True, exist_ok=True)
BANNED = {"\u2014": "em dash", "\u2013": "en dash", "\u00b7": "middle dot", "\u2026": "ellipsis"}

with sync_playwright() as p:
    b = p.chromium.launch(channel="msedge", headless=True)
    for vw, vh, tag in [(1920, 1080, "hd"), (1366, 768, "laptop"), (390, 844, "phone")]:
        page = b.new_page(viewport={"width": vw, "height": vh})
        errors, failed, external = [], [], []
        page.on("console", lambda m: errors.append(m.text) if m.type == "error" else None)
        page.on("pageerror", lambda e: errors.append(str(e)))
        page.on("response", lambda r: failed.append(f"{r.status} {r.url}") if r.status >= 400 else None)
        page.on("request", lambda r: external.append(r.url) if not r.url.startswith(url.split("/deck")[0]) else None)
        page.goto(url + "#1", wait_until="networkidle")
        page.evaluate("localStorage.clear()")
        page.wait_for_timeout(800)
        n = page.locator(".slide").count()
        for i in range(n):
            page.wait_for_timeout(700)
            if tag == "hd" or i in (0, 2):
                page.screenshot(path=str(out / f"{tag}_{i + 1}.png"))
            # text overflow check: any slide child extending past the 1080 canvas
            over = page.evaluate("""(i) => { const s = document.querySelectorAll('.slide')[i]; const r = s.getBoundingClientRect();
              const k = r.height / 1080; const bad = [];
              s.querySelectorAll('h1,h2,p,li,figure,table,.strip,.nums').forEach(e => { const q = e.getBoundingClientRect();
                if (q.bottom > r.bottom + 1 || q.right > r.right + 1) bad.push(e.tagName + '.' + e.className + ' ' + Math.round((q.bottom - r.top) / k) + 'x' + Math.round((q.right - r.left) / k)); });
              return bad; }""", i)
            if over:
                print(f"[{tag}] slide {i + 1} overflow:", over)
            page.keyboard.press("ArrowRight")
        text = page.evaluate("document.body.innerText")
        hits = {v: text.count(k) for k, v in BANNED.items() if k in text}
        print(f"[{tag}] slides {n} | console errors: {errors or 'none'} | failed: {failed or 'none'} | external: {external or 'none'} | banned glyphs: {hits or 'none'}")
        page.close()
    b.close()
