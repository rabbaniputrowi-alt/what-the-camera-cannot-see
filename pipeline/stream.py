"""Stream small windows out of NISAR GCOV scenes over HTTPS, without downloading the 5 GB files.

Usage: uv run python pipeline/stream.py --track 125 [--dates 2026-09-02 ...] [--windows w1 w2]

Reads EDL_TOKEN from .env and the scene list from data/gcov_scenes.json (made by search.py).
Each scene is opened once and every missing window is read from it. Output: data/win/<window>_t<track>_<date>.npz
with x, y, epsg, HHHH, HVHV (linear power, gamma0) plus mask, numberOfLooks and rtcGammaToSigmaFactor.
Files already on disk are skipped, so the script can be rerun after a dropped connection.
"""
import argparse, csv, json, os, sys, time
import numpy as np, h5py, fsspec
from pyproj import Transformer
from dotenv import dotenv_values
from config import ROOT, DATA, WIN_DIR, WINDOWS, win_path

ap = argparse.ArgumentParser()
ap.add_argument("--track", type=int, required=True)
ap.add_argument("--dates", nargs="*")
ap.add_argument("--windows", nargs="*", default=list(WINDOWS))
a = ap.parse_args()

tok = (dotenv_values(ROOT / ".env").get("EDL_TOKEN") or "").strip()
assert tok, "EDL_TOKEN is empty in .env"
scenes = sorted((s for s in json.load(open(DATA / "gcov_scenes.json")) if s["pathNumber"] == a.track),
                key=lambda s: s["startTime"])
if a.dates:
    scenes = [s for s in scenes if s["startTime"][:10] in a.dates]
WIN_DIR.mkdir(parents=True, exist_ok=True)
(ROOT / "logs").mkdir(exist_ok=True)
timings = open(ROOT / "logs" / "timings.csv", "a", newline="")
tw = csv.writer(timings)


def read_scene(url, date, todo):
    fs = fsspec.filesystem("http", headers={"Authorization": f"Bearer {tok}"},
                           cache_type="background", block_size=4 * 1024 * 1024)
    t0 = time.time()
    with fs.open(url, "rb") as f, h5py.File(f, "r") as h:
        g = h["/science/LSAR/GCOV/grids/frequencyA"]
        epsg = int(g["projection"][()])
        xs, ys = g["xCoordinates"][:], g["yCoordinates"][:]
        t_open = time.time() - t0
        tr = Transformer.from_crs(4326, epsg, always_xy=True)
        for w in todo:
            lon0, lat0, lon1, lat1 = WINDOWS[w]["bbox"]
            X, Y = tr.transform([lon0, lon1, lon0, lon1], [lat0, lat0, lat1, lat1])
            c0, c1 = int(np.searchsorted(xs, min(X))), int(np.searchsorted(xs, max(X)))
            if ys[0] > ys[-1]:
                r0, r1 = int(np.searchsorted(-ys, -max(Y))), int(np.searchsorted(-ys, -min(Y)))
            else:
                r0, r1 = int(np.searchsorted(ys, min(Y))), int(np.searchsorted(ys, max(Y)))
            t1 = time.time()
            out = {"x": xs[c0:c1], "y": ys[r0:r1], "epsg": epsg}
            for p in ("HHHH", "HVHV"):
                out[p] = g[p][r0:r1, c0:c1]
            for k in ("mask", "numberOfLooks", "rtcGammaToSigmaFactor"):
                if k in g:
                    try:
                        out[k] = g[k][r0:r1, c0:c1]
                    except Exception:
                        pass
            t_read = time.time() - t1
            dst = win_path(w, a.track, date)
            tmp = dst.with_suffix(".part.npz")
            np.savez_compressed(tmp, **out)
            os.replace(tmp, dst)
            print(f"{time.strftime('%H:%M:%S')} {date} t{a.track} {w}: open {t_open:.0f}s read {t_read:.0f}s "
                  f"shape {out['HVHV'].shape} epsg {epsg}", flush=True)
            tw.writerow([time.strftime("%Y-%m-%d %H:%M:%S"), date, a.track, w, f"{t_open:.1f}", f"{t_read:.1f}",
                         out["HVHV"].shape, epsg])
            timings.flush()


for s in scenes:
    date = s["startTime"][:10]
    inside = s.get("windows", a.windows)          # windows this scene's footprint contains (search.py)
    todo = [w for w in a.windows if w in inside and not win_path(w, a.track, date).exists()]
    if not todo:
        print(f"{date} t{a.track}: on disk, skipped", flush=True)
        continue
    for attempt in (1, 2, 3):
        try:
            read_scene(s["url"], date, todo)
            break
        except Exception as e:
            print(f"{date} t{a.track}: attempt {attempt} failed: {type(e).__name__} {str(e)[:120]}", flush=True)
            todo = [w for w in a.windows if w in inside and not win_path(w, a.track, date).exists()]
            time.sleep(5 * attempt)
print("done", flush=True)
