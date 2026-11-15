"""Optical burn map: HLS (Landsat 8 and 9 plus Sentinel-2, 30 m) Normalized Burn Ratio before and after the fires.

Usage: uv run python pipeline/hls_dnbr.py w1|w2
Reads EDL_TOKEN from .env. Writes data/hls/dnbr_<window>.npz (pre, post, dnbr on a 40 m grid matching the
first track's radar window, 125 for windows 1 to 4) and prints the clear share of every granule.

NBR = (NIR - SWIR2) / (NIR + SWIR2). dNBR = median NBR in July minus median NBR from October to mid November.
Cloud, cloud-adjacent, cloud shadow and water pixels are masked with HLS Fmask. Pixels flagged as high aerosol
are KEPT: Fmask flags the fire smoke itself as high aerosol over every pixel, so masking it would leave no
post-fire pixel at all. The after side of this map is therefore read through smoke.
"""
import os, sys, time
import numpy as np, rasterio, requests
from rasterio.warp import reproject, Resampling, transform_bounds
from rasterio.windows import from_bounds
from dotenv import dotenv_values
from config import ROOT, DATA, WINDOWS, BASELINE, win_path, window_tracks

W = sys.argv[1]
BBOX = ",".join(str(v) for v in WINDOWS[W]["bbox"])
PRE = ("2026-07-01", "2026-07-31")
POST = ("2026-10-01", "2026-11-13")
tok = (dotenv_values(ROOT / ".env").get("EDL_TOKEN") or "").strip()
assert tok, "EDL_TOKEN is empty in .env"
SES = requests.Session()
SES.headers["Authorization"] = f"Bearer {tok}"
os.environ["GDAL_DISABLE_READDIR_ON_OPEN"] = "EMPTY_DIR"
os.environ["CPL_VSIL_CURL_ALLOWED_EXTENSIONS"] = ".tif"


def signed(url):
    """LP DAAC redirects to a signed CloudFront URL. GDAL must be given that URL, not the bearer token."""
    r = SES.get(url, headers={"Range": "bytes=0-0"}, allow_redirects=True, timeout=60)
    r.close()
    return r.url


GRID_TRACK = window_tracks(W)[0]             # 125 for windows 1 to 4
z = np.load(win_path(W, GRID_TRACK, BASELINE[GRID_TRACK]))
x, y, epsg = z["x"][::4], z["y"][::4], int(z["epsg"])
dx, dy = x[1] - x[0], y[1] - y[0]
dst_tf = rasterio.transform.Affine(dx, 0, x[0] - dx / 2, 0, dy, y[0] - dy / 2)
H, Wd = len(y), len(x)


def granules(short_name, t0, t1):
    r = requests.get("https://cmr.earthdata.nasa.gov/search/granules.json", params={
        "short_name": short_name, "version": "2.0", "bounding_box": BBOX,
        "temporal": f"{t0}T00:00:00Z,{t1}T23:59:59Z", "page_size": 200}, timeout=60).json()
    out = []
    for e in r["feed"]["entry"]:
        links = {l["href"].split(".")[-2]: l["href"] for l in e["links"]
                 if l["href"].endswith(".tif") and l["href"].startswith("https")}
        out.append(dict(date=e["time_start"][:10], tile=e["title"].split(".")[2],
                        cloud=float(e.get("cloud_cover") or 100), links=links, sn=short_name))
    return out


def nbr_on_grid(g):
    nir, swir = ("B8A", "B12") if g["sn"] == "HLSS30" else ("B05", "B07")
    arrs = {}
    for b in (nir, swir, "Fmask"):
        fill = 255 if b == "Fmask" else -9999
        with rasterio.open(signed(g["links"][b])) as src:
            sb = transform_bounds(f"EPSG:{epsg}", src.crs, x.min() - 100, y.min() - 100, x.max() + 100, y.max() + 100)
            win = from_bounds(*sb, transform=src.transform).round_offsets().round_lengths()
            a = src.read(1, window=win, boundless=True, fill_value=fill)
            dst = np.full((H, Wd), 255 if b == "Fmask" else np.nan, dtype="float32")
            reproject(a.astype("float32"), dst, src_transform=src.window_transform(win), src_crs=src.crs,
                      dst_transform=dst_tf, dst_crs=f"EPSG:{epsg}", resampling=Resampling.nearest,
                      src_nodata=fill, dst_nodata=255 if b == "Fmask" else np.nan)
            arrs[b] = dst
    fm = np.where(np.isfinite(arrs["Fmask"]), arrs["Fmask"], 255).astype(np.int32)
    # Fmask bits: 1 cloud, 2 adjacent to cloud or shadow, 3 cloud shadow, 5 water. Bits 6 and 7 (aerosol) are not used.
    bad = (fm == 255) | ((fm >> 1) & 1).astype(bool) | ((fm >> 2) & 1).astype(bool) \
        | ((fm >> 3) & 1).astype(bool) | ((fm >> 5) & 1).astype(bool)
    n, s = arrs[nir], arrs[swir]
    with np.errstate(all="ignore"):
        nbr = (n - s) / (n + s)
    nbr[bad | ~np.isfinite(nbr) | (n <= 0)] = np.nan
    return nbr


def composite(t0, t1, max_cloud):
    stack, info = [], []
    for g in [g for sn in ("HLSS30", "HLSL30") for g in granules(sn, t0, t1) if g["cloud"] <= max_cloud]:
        t = time.time()
        try:
            a = nbr_on_grid(g)
        except Exception as e:
            info.append((g["date"], g["tile"], g["sn"], "ERR " + type(e).__name__))
            continue
        clear = float(np.isfinite(a).mean())
        info.append((g["date"], g["tile"], g["sn"], round(clear, 3), round(time.time() - t, 1)))
        if clear > 0.02:
            stack.append(a)
    return np.array(stack), info


pre_s, pre_i = composite(*PRE, 35)
with np.errstate(all="ignore"):
    pre_clear = float(np.isfinite(np.nanmedian(pre_s, axis=0)).mean()) if len(pre_s) else 0.0
if pre_clear < 0.5:
    # Added 2026-11-15 for windows 7 and 8, where the July tiles under 35% cloud leave less than half the window
    # clear (w7 0.33, w8 none). Same cut as the after side; clouds are still masked pixel by pixel. Windows 1 to 6
    # have July composites 0.79 to 1.00 clear and are unaffected.
    print(f"pre: composite only {pre_clear:.2f} clear with tiles under 35% cloud, falling back to 80%", flush=True)
    pre_s, pre_i = composite(*PRE, 80)
print("pre", pre_i, flush=True)
post_s, post_i = composite(*POST, 80)
print("post", post_i, flush=True)
with np.errstate(all="ignore"):
    pre, post = np.nanmedian(pre_s, axis=0), np.nanmedian(post_s, axis=0)
(DATA / "hls").mkdir(parents=True, exist_ok=True)
np.savez_compressed(DATA / "hls" / f"dnbr_{W}.npz", pre=pre, post=post, dnbr=pre - post, x=x, y=y, epsg=epsg)
d = pre - post
print("clear share", round(float(np.isfinite(d).mean()), 3), "dNBR above 0.27:", round(float(np.nanmean(d > 0.27)), 3))
