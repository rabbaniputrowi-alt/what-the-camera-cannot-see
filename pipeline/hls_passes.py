"""Every optical pass of the season, not only the ones nearest a radar pass.

Usage: uv run python pipeline/hls_passes.py w1|w2 [--workers 6]
Reads EDL_TOKEN from .env. Lists every HLS v2.0 acquisition (Landsat 8 and 9, Sentinel-2) that touches the
window between 10 June and 13 November 2026 and, for each sensor-day, writes
  docs/data/passes/<window>_<date>_<L|S>.webp   small true-colour image, nothing masked or altered
  docs/data/passes_<window>.json                per pass: share of the window covered, and what HLS's own
                                                quality mask (Fmask) calls cloud, cloud shadow, high aerosol
The rule for a "usable look" was fixed before counting and lives in config.py (USABLE_COVER, USABLE_CLOUD):
the pass covers at least 90% of the window and Fmask calls less than half of the covered part cloud.
Results are written after every pass, so an interrupted run can be resumed.
"""
import argparse, json, os, threading, time
from concurrent.futures import ThreadPoolExecutor, as_completed
import numpy as np, rasterio, requests
from PIL import Image
from rasterio.transform import from_bounds
from rasterio.warp import reproject, Resampling, transform_bounds
from rasterio.windows import from_bounds as window_from_bounds
from dotenv import dotenv_values
from config import ROOT, SITE_DATA, WINDOWS, USABLE_COVER, USABLE_CLOUD

ap = argparse.ArgumentParser()
ap.add_argument("window")
ap.add_argument("--workers", type=int, default=6)
a = ap.parse_args()
W = a.window
west, south, east, north = WINDOWS[W]["bbox"]
PX = 740                                   # about 30 m, the native HLS pixel
THUMB = 296
DST_TF = from_bounds(west, south, east, north, PX, PX)
SENSOR = {"HLSS30": "Sentinel-2", "HLSL30": "Landsat"}
tok = (dotenv_values(ROOT / ".env").get("EDL_TOKEN") or "").strip()
assert tok, "EDL_TOKEN is empty in .env"
os.environ["GDAL_DISABLE_READDIR_ON_OPEN"] = "EMPTY_DIR"
os.environ["CPL_VSIL_CURL_ALLOWED_EXTENSIONS"] = ".tif"
OUT = SITE_DATA / "passes"
OUT.mkdir(parents=True, exist_ok=True)
INDEX = SITE_DATA / f"passes_{W}.json"
local = threading.local()


def session():
    if not hasattr(local, "s"):
        local.s = requests.Session()
        local.s.headers["Authorization"] = f"Bearer {tok}"
    return local.s


def signed(url):
    """LP DAAC redirects to a signed CloudFront URL. GDAL must be given that URL, not the bearer token."""
    r = session().get(url, headers={"Range": "bytes=0-0"}, allow_redirects=True, timeout=60)
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
    """One band of one granule on the window grid (NaN where the granule has no data). Retries twice."""
    for attempt in (1, 2, 3):
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
            if attempt == 3:
                raise
            time.sleep(4 * attempt)


def mosaic(gs, name, fill, how):
    out = np.full((PX, PX), np.nan, "float32")
    for g in gs:
        out = np.where(np.isfinite(out), out, band(g, name, fill, how))
    return out


def one_pass(key, gs):
    date, sn = key
    fm = mosaic(gs, "Fmask", 255, Resampling.nearest)
    ok = np.isfinite(fm)
    cover = float(ok.mean())
    rec = {"date": date, "sensor": SENSOR[sn], "tiles": sorted(g["tile"] for g in gs), "coverage": round(cover, 3)}
    if cover < 0.02:
        return rec
    f = np.where(ok, fm, 0).astype(np.int32)
    n = int(ok.sum())
    share = lambda m: round(float((m & ok).sum()) / n, 3)
    cloud = ((f >> 1) & 1).astype(bool)
    near = ((f >> 2) & 1).astype(bool)
    shadow = ((f >> 3) & 1).astype(bool)
    aero = ((f >> 6) & 3) == 3
    rec.update(cloud=share(cloud), cloud_shadow=share(shadow), near_cloud=share(near), high_aerosol=share(aero),
               not_cloud_or_shadow=share(~cloud & ~shadow))
    rec["usable"] = bool(cover >= USABLE_COVER and rec["cloud"] < USABLE_CLOUD)
    rgb = np.dstack([mosaic(gs, b, -9999, Resampling.bilinear) for b in ("B04", "B03", "B02")])
    v = np.clip(rgb * 0.0001 / 0.32, 0, 1) ** 0.75          # surface reflectance 0 to 0.32, mild brightening
    v = np.where(np.isfinite(v), v, 0)
    name = f"{W}_{date}_{'L' if sn == 'HLSL30' else 'S'}.webp"
    Image.fromarray((v * 255).round().astype("uint8"), "RGB").resize((THUMB, THUMB), Image.LANCZOS).save(
        OUT / name, "WEBP", quality=72, method=5)
    rec["file"] = f"passes/{name}"
    return rec


allg = [g for sn in SENSOR for g in granules(sn)]
by_day = {}
for g in allg:
    by_day.setdefault((g["date"], g["sn"]), []).append(g)
done = {}
if INDEX.exists():
    done = {(r["date"], r["sensor"]): r for r in json.load(open(INDEX))["passes"]}
todo = {k: v for k, v in by_day.items() if (k[0], SENSOR[k[1]]) not in done}
print(f"{W}: {len(allg)} HLS granules on {len(by_day)} sensor-days, {len(todo)} to read", flush=True)


def save():
    rows = sorted(done.values(), key=lambda r: (r["date"], r["sensor"]))
    json.dump({"window": W, "rule": {"min_coverage": USABLE_COVER, "max_cloud": USABLE_CLOUD},
               "period": ["2026-06-10", "2026-11-13"], "passes": rows}, open(INDEX, "w"), indent=1)


t0 = time.time()
failed = []
with ThreadPoolExecutor(a.workers) as ex:
    futs = {ex.submit(one_pass, k, v): k for k, v in sorted(todo.items())}
    for i, fu in enumerate(as_completed(futs), 1):
        k = futs[fu]
        try:
            r = fu.result()
        except Exception as e:
            failed.append(k)
            print(f"  FAILED {k}: {type(e).__name__} {str(e)[:120]}", flush=True)
            continue
        done[(r["date"], r["sensor"])] = r
        save()
        print(f"[{i}/{len(futs)} {time.time() - t0:5.0f}s] {r['date']} {r['sensor']:10s} cover {r['coverage']:.2f} "
              f"cloud {r.get('cloud', '-')} usable {r.get('usable', '-')}", flush=True)
save()
print(f"done in {time.time() - t0:.0f}s, {len(failed)} failed: {failed}", flush=True)
