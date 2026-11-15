"""Build the images and numbers the demo deck (docs/deck/) reads.

Usage: uv run python pipeline/build_deck.py
Needs the overlays saved from the running page into logs/deck/ (tests/deck_overlays.py) and the
files build_site.py and score.py already wrote into docs/data/.
"""
import json
from pathlib import Path
from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "docs" / "data"
OUT = ROOT / "docs" / "deck" / "img"
OUT.mkdir(parents=True, exist_ok=True)
LOG = ROOT / "logs" / "deck"


def save(im, name, size=None, q=82):
    if size:
        im = im.resize((size, size), Image.LANCZOS)
    im.convert("RGB").save(OUT / name, "WEBP", quality=q)


def radar(date, track=125, pol="hv"):
    return Image.open(DATA / "img" / f"w1_t{track}_{date}_{pol}.webp").convert("RGBA")


# Radar before and after, window 1, track 125, with the change layer from the page on the after image.
before = radar("2026-07-16")
after = radar("2026-10-20")
ov = Image.open(LOG / "ov_change_fire.png").convert("RGBA")
save(before, "radar_before.webp", 900)
save(Image.alpha_composite(after, ov), "radar_after_change.webp", 900)
save(after, "radar_after.webp", 900)
plac = radar("2026-07-04")
ovp = Image.open(LOG / "ov_change_placebo.png").convert("RGBA")
save(Image.alpha_composite(radar("2026-07-16"), ovp), "radar_placebo_change.webp", 600)
save(Image.alpha_composite(after, ov), "radar_fire_change_small.webp", 600)

# Same day, two satellites: the camera on 20 Oct against the radar on 20 Oct.
shot = LOG / "app_default.png"
if shot.exists():   # the application's first screen, from tests/deck_overlays.py
    Image.open(shot).convert("RGB").save(OUT / "app.webp", "WEBP", quality=85)
cam = Image.open(DATA / "opt" / "w1_2026-10-20_L.webp")
save(cam, "camera_20oct.webp", 720)
save(after, "radar_20oct.webp", 720)
save(Image.open(DATA / "opt" / "w1_2026-10-04_L.webp"), "camera_04oct.webp", 720)

# The peak period, every optical pass and every radar pass over window 1.
passes = json.load(open(DATA / "passes_w1.json"))
meta = json.load(open(DATA / "meta.json"))
w1 = meta["windows"]["w1"]
PEAK = ("2026-09-15", "2026-11-01")
opt = [p for p in passes["passes"] if PEAK[0] <= p["date"] <= PEAK[1] and p["coverage"] >= 0.9]
rad = sorted(
    (d, t) for t, tr in w1["tracks"].items() for d in tr["dates"] if PEAK[0] <= d <= PEAK[1]
)
strip = {"optical": [], "radar": []}
for p in opt:
    name = "pass_" + Path(p["file"]).name
    save(Image.open(DATA / p["file"]), name, 220, 78)
    strip["optical"].append({"date": p["date"], "sensor": p["sensor"], "usable": p["usable"],
                             "cloud": round(p["cloud"], 2), "img": "img/" + name})
for d, t in rad:
    name = f"rpass_{t}_{d}.webp"
    save(radar(d, int(t)), name, 220, 78)
    strip["radar"].append({"date": d, "track": int(t), "img": "img/" + name})

# Season curve for window 1 on both tracks, and the summary rows for every window.
scores = json.load(open(DATA / "scores.json"))
curve = {}
summary = []
for s in scores:
    key = f"{s['window']}_{s['track']}"
    pairs = s["pairs"]
    if s["window"] == "w1":
        curve[str(s["track"])] = [
            {"to": p["to"], "from": p["from"], "kind": p["kind"], "hv": round(p["hv_auc"], 3)}
            for p in pairs if p["hv_auc"] is not None
        ]
    pl = [p["hv_auc"] for p in pairs if p["kind"] == "placebo" and p["hv_auc"] is not None]
    fire = [p for p in pairs if p["kind"] == "fire" and p["hv_auc"] is not None]
    hh_fire = [p["hh_auc"] for p in fire if p.get("hh_auc") is not None]
    summary.append({"key": key, "window": s["window"], "track": s["track"],
                    "placebo": [round(x, 2) for x in pl],
                    "fire_max": round(max(p["hv_auc"] for p in fire), 2) if fire else None,
                    "hh_fire_max": round(max(hh_fire), 2) if hh_fire else None})

windows = {k: {"label": v["label"], "bbox": v["bbox"]} for k, v in meta["windows"].items()}
json.dump({"strip": strip, "curve": curve, "summary": summary, "windows": windows},
          open(ROOT / "docs" / "deck" / "deck.json", "w"), indent=1)
print("optical peak passes:", len(opt), "usable:", sum(p["usable"] for p in opt), "| radar:", len(rad))
print("wrote", len(list(OUT.iterdir())), "images")
