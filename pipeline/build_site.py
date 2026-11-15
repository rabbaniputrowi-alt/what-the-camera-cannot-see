"""Build every file the page reads, from the streamed NISAR windows, the HLS burn map and the FIRMS points.

Usage: uv run python pipeline/build_site.py [--force]

All layers of a window are resampled onto one lon/lat display grid (DISPLAY_PX square, about 20 m per pixel),
so both tracks, the optical burn map and the hotspots line up pixel for pixel.

Outputs in docs/data/:
  img/<window>_t<track>_<date>_<hv|hh>.webp   backscatter in dB, grey, fixed stretch per polarization
  cells_<window>_t<track>.bin                 200 m cell means in dB x 100, int16, order: date, polarization (HV, HH), row, col
  labels_<window>.bin                         200 m optical labels, uint8 (see LABELS below)
  optical_<window>.png                        HLS dNBR classes as a transparent overlay
  hotspots_<window>.json                      VIIRS detections inside the window
  meta.json                                   everything the page needs to find and read the files above
"""
import argparse, json, time
import numpy as np, pandas as pd
from PIL import Image
from rasterio.transform import Affine, from_bounds
from rasterio.warp import reproject, Resampling
from scipy.ndimage import uniform_filter
from config import (DATA, SITE_DATA, WINDOWS, TRACKS, BASELINE, PRE_SEASON_END, DISPLAY_PX, CELL_PX,
                    HV_STRETCH_DB, HH_STRETCH_DB, SPECKLE_BOX, DNBR_BURNED, DNBR_SEVERE, DNBR_UNBURNED,
                    HV_RULE_DB, PERIODS, THUMB_PX, USABLE_COVER, ROOT, win_path, dates_on_disk)

ap = argparse.ArgumentParser()
ap.add_argument("--force", action="store_true", help="re-render images that already exist")
a = ap.parse_args()

LABELS = {0: "no clear optical view", 1: "unburned (dNBR below 0.10)", 2: "in between, not scored",
          3: "burned (dNBR above 0.27)", 4: "severely burned (dNBR above 0.44)"}
NCELL = DISPLAY_PX // CELL_PX
IMG = SITE_DATA / "img"
IMG.mkdir(parents=True, exist_ok=True)
PASSES = SITE_DATA / "passes"
PASSES.mkdir(parents=True, exist_ok=True)
MONTHS = "Jan Feb Mar Apr May Jun Jul Aug Sep Oct Nov Dec".split()
day = lambda d: f"{int(d[8:])} {MONTHS[int(d[5:7]) - 1]}"


def display_tf(bbox):
    west, south, east, north = bbox
    return from_bounds(west, south, east, north, DISPLAY_PX, DISPLAY_PX)


def to_display(arr, x, y, epsg, bbox, how):
    """Resample a north-up raster with pixel-centre coordinates x, y onto the window's display grid."""
    dx, dy = x[1] - x[0], y[1] - y[0]
    src_tf = Affine(dx, 0, x[0] - dx / 2, 0, dy, y[0] - dy / 2)
    dst = np.full((DISPLAY_PX, DISPLAY_PX), np.nan, "float32")
    reproject(arr.astype("float32"), dst, src_transform=src_tf, src_crs=f"EPSG:{epsg}",
              dst_transform=display_tf(bbox), dst_crs="EPSG:4326", resampling=how,
              src_nodata=np.nan, dst_nodata=np.nan)
    return dst


def boxcar(p, k):
    """Mean filter in linear power that ignores missing pixels."""
    ok = np.isfinite(p)
    num = uniform_filter(np.where(ok, p, 0.0), k, mode="nearest")
    den = uniform_filter(ok.astype("float32"), k, mode="nearest")
    with np.errstate(all="ignore"):
        return np.where(den > 0, num / den, np.nan)


def cells(p):
    """Mean of each CELL_PX square block (about 200 m)."""
    b = p[:NCELL * CELL_PX, :NCELL * CELL_PX].reshape(NCELL, CELL_PX, NCELL, CELL_PX)
    with np.errstate(all="ignore"):
        return np.nanmean(b, axis=(1, 3))


def save_grey(db, stretch, path):
    lo, hi = stretch
    g = np.clip((db - lo) / (hi - lo), 0, 1)
    g = np.where(np.isfinite(g), g, 0)
    Image.fromarray((g * 255).round().astype("uint8"), "L").save(path, "WEBP", quality=82, method=5)


meta = {"built": time.strftime("%Y-%m-%d %H:%M"), "display_px": DISPLAY_PX, "cell_px": CELL_PX, "ncell": NCELL,
        "cell_scale": 100, "cell_nodata": -32768, "pols": ["hv", "hh"], "labels": LABELS,
        "stretch_db": {"hv": HV_STRETCH_DB, "hh": HH_STRETCH_DB}, "rule_db": HV_RULE_DB,
        "dnbr": {"burned": DNBR_BURNED, "severe": DNBR_SEVERE, "unburned": DNBR_UNBURNED},
        "pre_season_end": PRE_SEASON_END, "windows": {}}

hot = pd.read_csv(DATA / "firms" / "hotspots.csv")
hot = hot[hot.source.str.startswith("VIIRS")]

for w, wc in WINDOWS.items():
    if not (DATA / "hls" / f"dnbr_{w}.npz").exists():
        print(f"{w}: no optical burn map yet (run hls_dnbr.py {w}), window left out", flush=True)
        continue
    bbox = wc["bbox"]
    west, south, east, north = bbox
    wm = {"label": wc["label"], "bbox": bbox, "tracks": {}}

    # radar: display images and 200 m cells
    for tr, tc in TRACKS.items():
        dates = dates_on_disk(w, tr)
        if not dates:
            continue
        stack = np.full((len(dates), 2, NCELL, NCELL), -32768, "int16")
        for i, d in enumerate(dates):
            z = np.load(win_path(w, tr, d))
            for j, (pol, key, stretch) in enumerate((("hv", "HVHV", HV_STRETCH_DB), ("hh", "HHHH", HH_STRETCH_DB))):
                p = z[key].astype("float32")
                p[~np.isfinite(p) | (p <= 0)] = np.nan
                disp = to_display(p, z["x"], z["y"], int(z["epsg"]), bbox, Resampling.average)
                with np.errstate(all="ignore"):
                    c = 10 * np.log10(cells(disp))
                stack[i, j] = np.where(np.isfinite(c), np.round(c * 100), -32768).astype("int16")
                out = IMG / f"{w}_t{tr}_{d}_{pol}.webp"
                if a.force or not out.exists():
                    with np.errstate(all="ignore"):
                        save_grey(10 * np.log10(boxcar(disp, SPECKLE_BOX)), stretch, out)
                thumb = PASSES / f"{w}_t{tr}_{d}_hv.webp"
                if pol == "hv" and (a.force or not thumb.exists()):
                    Image.open(out).resize((THUMB_PX, THUMB_PX), Image.LANCZOS).save(thumb, "WEBP", quality=75, method=5)
            print(f"{w} t{tr} {d}", flush=True)
        stack.astype("<i2").tofile(SITE_DATA / f"cells_{w}_t{tr}.bin")
        pre = [d for d in dates if d <= PRE_SEASON_END]
        wm["tracks"][str(tr)] = {"direction": tc["direction"], "dates": dates, "baseline": BASELINE[tr],
                                 "pre_season": pre, "cells": f"cells_{w}_t{tr}.bin"}

    # optical truth: HLS dNBR on the display grid, then 200 m labels
    o = np.load(DATA / "hls" / f"dnbr_{w}.npz")
    dn = to_display(o["dnbr"], o["x"], o["y"], int(o["epsg"]), bbox, Resampling.nearest)
    clear = cells(np.isfinite(dn).astype("float32"))
    dc = cells(dn)
    lab = np.zeros((NCELL, NCELL), "uint8")
    ok = clear > 0.5
    lab[ok & (dc < DNBR_UNBURNED)] = 1
    lab[ok & (dc >= DNBR_UNBURNED) & (dc <= DNBR_BURNED)] = 2
    lab[ok & (dc > DNBR_BURNED)] = 3
    lab[ok & (dc > DNBR_SEVERE)] = 4
    lab.tofile(SITE_DATA / f"labels_{w}.bin")
    rgba = np.zeros((DISPLAY_PX, DISPLAY_PX, 4), "uint8")
    rgba[~np.isfinite(dn)] = (120, 130, 140, 150)          # no clear optical pixel
    rgba[dn > DNBR_BURNED] = (255, 150, 30, 190)           # burned
    rgba[dn > DNBR_SEVERE] = (200, 30, 30, 210)            # severe
    Image.fromarray(rgba, "RGBA").resize((DISPLAY_PX // 2, DISPLAY_PX // 2), Image.NEAREST).save(
        SITE_DATA / f"optical_{w}.png", optimize=True)
    wm["optical"] = {"overlay": f"optical_{w}.png", "labels": f"labels_{w}.bin",
                     "clear_share": round(float(np.isfinite(dn).mean()), 3),
                     "counts": {str(k): int((lab == k).sum()) for k in LABELS}}

    # hotspots: VIIRS detections inside the window
    h = hot[(hot.longitude >= west) & (hot.longitude <= east) & (hot.latitude >= south) & (hot.latitude <= north)]
    h = h.sort_values(["acq_date", "acq_time"])
    pts = [[round((lo - west) / (east - west), 4), round((north - la) / (north - south), 4), d]
           for lo, la, d in zip(h.longitude, h.latitude, h.acq_date)]
    json.dump({"fields": ["x", "y", "date"], "points": pts}, open(SITE_DATA / f"hotspots_{w}.json", "w"),
              separators=(",", ":"))
    wm["hotspots"] = {"file": f"hotspots_{w}.json", "count": len(pts),
                      "first": str(hot.acq_date.min()), "last": str(hot.acq_date.max())}

    # the camera side: HLS true-colour image nearest each NISAR pass (made by hls_rgb.py), if present
    cam = DATA / "hls" / f"camera_{w}.json"
    if cam.exists():
        wm["camera"] = json.load(open(cam))
    # every optical pass of the season (made by hls_passes.py), counted per period next to the radar passes
    pj = SITE_DATA / f"passes_{w}.json"
    if pj.exists():
        P = json.load(open(pj))["passes"]
        radar = sorted((d, tr) for tr, t in wm["tracks"].items() for d in t["dates"])
        listed = sorted({(s["startTime"][:10], str(s["pathNumber"])) for s in json.load(open(DATA / "gcov_scenes.json"))
                         if w in s.get("windows", [w])})
        per = []
        for lo, hi, name in PERIODS:
            q = [p for p in P if lo <= p["date"] <= hi]
            full = [p for p in q if p["coverage"] >= USABLE_COVER]      # only full passes are counted
            per.append({"from": lo, "to": hi, "label": name, "optical": len(full), "partial": len(q) - len(full),
                        "usable": sum(bool(p.get("usable")) for p in q),
                        "usable_dates": [p["date"] for p in q if p.get("usable")],
                        "radar": sum(lo <= d <= hi for d, _ in listed),          # NISAR scenes in the archive
                        "radar_ok": sum(lo <= d <= hi for d, _ in radar)})       # of which read into this window
        wm["passes"] = {"file": f"passes_{w}.json", "periods": per, "note": wc.get("pass_note", ""),
                        "radar": [{"date": d, "track": tr, "file": f"passes/{w}_t{tr}_{d}_hv.webp"} for d, tr in radar]}
    meta["windows"][w] = wm
    print(f"{w}: labels {wm['optical']['counts']}, clear {wm['optical']['clear_share']}, hotspots {len(pts)}", flush=True)

json.dump(meta, open(SITE_DATA / "meta.json", "w"), indent=1)

# README table of the pass count, between its markers: one row per window, usable looks of full optical passes
rows = ["| Window | " + " | ".join(f"{name}, {day(lo)} to {day(hi)}" for lo, hi, name in PERIODS) +
        " | NISAR passes with data, peak |", "|---|" + "---|" * (len(PERIODS) + 1)]
cell = lambda p: (f"{p['usable']} of {p['optical']}" +
                  (f" ({', '.join(day(d) for d in p['usable_dates'])})" if 0 < p["usable"] <= 2 else ""))
built = [w for w in WINDOWS if w in meta["windows"] and meta["windows"][w].get("passes")]
if built:
    for w in built:
        per = meta["windows"][w]["passes"]["periods"]
        rows.append(f"| {meta['windows'][w]['label']} | " + " | ".join(cell(p) for p in per) +
                    f" | {per[-1]['radar_ok']} of {per[-1]['radar']} |")
    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    if "<!-- passes:start" in readme:
        head, rest = readme.split("<!-- passes:start", 1)
        marker, tail = rest.split("-->", 1)[0], rest.split("<!-- passes:end -->", 1)[1]
        NL = chr(10)
        (ROOT / "README.md").write_text(head + "<!-- passes:start" + marker + "-->" + NL + NL.join(rows) + NL +
                                        "<!-- passes:end -->" + tail, encoding="utf-8", newline=NL)
    print(*rows, sep=chr(10))
print("wrote", SITE_DATA / "meta.json")
