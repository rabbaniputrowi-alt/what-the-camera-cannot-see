"""The camera side: HLS true-colour images (Landsat 8 and 9, Sentinel-2) nearest in time to each NISAR pass.

Usage: uv run python pipeline/hls_rgb.py w1|w2 [--max-days 3]
Reads EDL_TOKEN from .env. For every NISAR pass it takes the HLS acquisition closest in time (same day
if there is one) that covers the window, and writes docs/data/opt/<window>_<hls date>_<sensor>.webp plus
data/hls/camera_<window>.json with, per NISAR date, the HLS date, the sensor and what HLS's own quality mask
(Fmask) says about the scene: share of cloud, of cloud shadow, and of pixels flagged as high aerosol.
No pixel is masked or altered: the image is what the optical sensor recorded.
"""
import argparse, datetime as dt, json, os, time
import numpy as np, rasterio, requests
from PIL import Image
from rasterio.transform import from_bounds
from rasterio.warp import reproject, Resampling, transform_bounds
from rasterio.windows import from_bounds as window_from_bounds
from dotenv import dotenv_values
from config import ROOT, DATA, SITE_DATA, WINDOWS

ap = argparse.ArgumentParser()
ap.add_argument("window")
ap.add_argument("--max-days", type=int, default=3)
a = ap.parse_args()
W = a.window
west, south, east, north = WINDOWS[W]["bbox"]
PX = 740                                   # about 30 m, the native HLS pixel
DST_TF = from_bounds(west, south, east, north, PX, PX)
SENSOR = {"HLSS30": "Sentinel-2", "HLSL30": "Landsat"}
tok = (dotenv_values(ROOT / ".env").get("EDL_TOKEN") or "").strip()
assert tok, "EDL_TOKEN is empty in .env"
SES = requests.Session()
SES.headers["Authorization"] = f"Bearer {tok}"
os.environ["GDAL_DISABLE_READDIR_ON_OPEN"] = "EMPTY_DIR"
os.environ["CPL_VSIL_CURL_ALLOWED_EXTENSIONS"] = ".tif"
OUT = SITE_DATA / "opt"
OUT.mkdir(parents=True, exist_ok=True)


def signed(url):
    """LP DAAC redirects to a signed CloudFront URL. GDAL must be given that URL, not the bearer token."""
    r = SES.get(url, headers={"Range": "bytes=0-0"}, allow_redirects=True, timeout=60)
    r.close()
    return r.url


def granules(short_name):
    r = requests.get("https://cmr.earthdata.nasa.gov/search/granules.json", params={
        "short_name": short_name, "version": "2.0", "bounding_box": f"{west},{south},{east},{north}",
        "temporal": "2026-06-10T00:00:00Z,2026-11-13T23:59:59Z", "page_size": 500}, timeout=60).json()
    out = []
    for e in r["feed"]["entry"]:
        links = {l["href"].split(".")[-2]: l["href"] for l in e["links"]
                 if l["href"].endswith(".tif") and l["href"].startswith("https")}
        out.append(dict(date=e["time_start"][:10], tile=e["title"].split(".")[2], links=links, sn=short_name))
    return out


def band(g, name, fill, how):
    """One band of one granule on the window grid (NaN where the granule has no data). Retries once."""
    for attempt in (1, 2):
        try:
            with rasterio.open(signed(g["links"][name])) as src:
                sb = transform_bounds("EPSG:4326", src.crs, west - 0.005, south - 0.005, east + 0.005, north + 0.005)
                win = window_from_bounds(*sb, transform=src.transform).round_offsets().round_lengths()
                arr = src.read(1, window=win, boundless=True, fill_value=fill)
                dst = np.full((PX, PX), np.nan, "float32")
                reproject(arr.astype("float32"), dst, src_transform=src.window_transform(win), src_crs=src.crs,
                          dst_transform=DST_TF, dst_crs="EPSG:4326", resampling=how, src_nodata=fill, dst_nodata=np.nan)
            return dst
        except Exception:
            if attempt == 2:
                raise
            time.sleep(3)


def mosaic(gs, name, fill, how):
    out = np.full((PX, PX), np.nan, "float32")
    for g in gs:
        b = band(g, name, fill, how)
        out = np.where(np.isfinite(out), out, b)
    return out


allg = [g for sn in SENSOR for g in granules(sn)]
by_day = {}
for g in allg:
    by_day.setdefault((g["date"], g["sn"]), []).append(g)
print(f"{W}: {len(allg)} HLS granules on {len(by_day)} sensor-days", flush=True)

nisar = sorted({s["startTime"][:10] for s in json.load(open(DATA / "gcov_scenes.json")) if W in s.get("windows", [W])})
day = lambda s: dt.date.fromisoformat(s)
index_path = DATA / "hls" / f"camera_{W}.json"
prev = json.load(open(index_path)) if index_path.exists() else {}
done, index = {}, {}
for nd in nisar:
    if prev.get(nd):                      # already matched in an earlier run: keep it, read nothing
        index[nd] = prev[nd]
        continue
    cands = sorted((k for k in by_day if abs((day(k[0]) - day(nd)).days) <= a.max_days),
                   key=lambda k: (abs((day(k[0]) - day(nd)).days), k[1] != "HLSL30"))
    pick = None
    for k in cands:
        if k not in done:
            t = time.time()
            try:
                fm = mosaic(by_day[k], "Fmask", 255, Resampling.nearest)
            except Exception as e:
                print(f"  {k} Fmask failed: {type(e).__name__}", flush=True)
                continue
            cover = float(np.isfinite(fm).mean())
            done[k] = {"fmask": fm, "coverage": cover, "t": time.time() - t}
        if done[k]["coverage"] >= 0.9:
            pick = k
            break
    if pick is None:
        print(f"{nd}: no HLS acquisition within {a.max_days} days covers the window", flush=True)
        index[nd] = None
        continue
    info = done[pick]
    name = f"{W}_{pick[0]}_{'L' if pick[1] == 'HLSL30' else 'S'}.webp"
    if "stats" not in info:
        fm = info["fmask"]
        ok = np.isfinite(fm)
        f = np.where(ok, fm, 0).astype(np.int32)
        n = max(int(ok.sum()), 1)
        share = lambda m: round(float((m & ok).sum()) / n, 3)
        cloud = ((f >> 1) & 1).astype(bool)
        shadow = ((f >> 3) & 1).astype(bool)
        aero = ((f >> 6) & 3) == 3
        info["stats"] = {"cloud": share(cloud), "cloud_shadow": share(shadow), "high_aerosol": share(aero),
                         "cloud_or_high_aerosol": share(cloud | aero),
                         "neither": share(~cloud & ~shadow & ~aero)}
        try:
            rgb = np.dstack([mosaic(by_day[pick], b, -9999, Resampling.bilinear) for b in ("B04", "B03", "B02")])
        except Exception as e:
            print(f"  {pick} bands failed: {type(e).__name__}", flush=True)
            index[nd] = None
            continue
        v = np.clip(rgb * 0.0001 / 0.32, 0, 1) ** 0.75          # surface reflectance 0 to 0.32, mild brightening
        v = np.where(np.isfinite(v), v, 0)
        Image.fromarray((v * 255).round().astype("uint8"), "RGB").save(OUT / name, "WEBP", quality=80, method=5)
    index[nd] = {"file": f"opt/{name}", "hls_date": pick[0], "sensor": SENSOR[pick[1]],
                 "days_apart": (day(pick[0]) - day(nd)).days, "coverage": round(info["coverage"], 3), **info["stats"]}
    print(f"{nd}: {SENSOR[pick[1]]} {pick[0]} {info['stats']}", flush=True)
    json.dump(index, open(index_path, "w"), indent=1)
json.dump(index, open(index_path, "w"), indent=1)
print("done", flush=True)
