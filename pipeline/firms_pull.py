"""Pull VIIRS and MODIS active-fire detections for the study region from the NASA FIRMS area API.

Usage: uv run python pipeline/firms_pull.py
Reads FIRMS_MAP_KEY from .env (free key: https://firms.modaps.eosdis.nasa.gov/api/map_key/).
Appends to data/firms/hotspots.csv with a `source` column. The API returns at most 5 days per call,
and for the current year only the near real-time (NRT) sources have data.
"""
import datetime as dt, io, os
import pandas as pd, requests
from dotenv import dotenv_values
from config import ROOT, DATA

KEY = (dotenv_values(ROOT / ".env").get("FIRMS_MAP_KEY") or "").strip()
assert KEY, "FIRMS_MAP_KEY is empty in .env"
BOX = "113.5,-3.5,114.8,-2.0"          # west, south, east, north: both windows with a margin
START, END = dt.date(2026, 6, 15), dt.date(2026, 11, 13)
SOURCES = ["VIIRS_SNPP_NRT", "VIIRS_NOAA20_NRT", "VIIRS_NOAA21_NRT", "MODIS_NRT"]
out = DATA / "firms" / "hotspots.csv"
out.parent.mkdir(parents=True, exist_ok=True)
assert not out.exists(), f"{out} exists; move it away before pulling again (this script appends)"

for s in SOURCES:
    d, n = START, 0
    while d <= END:
        url = f"https://firms.modaps.eosdis.nasa.gov/api/area/csv/{KEY}/{s}/{BOX}/5/{d}"
        try:
            t = requests.get(url, timeout=60).text
        except Exception as e:
            print(s, d, "ERR", type(e).__name__, flush=True)
            d += dt.timedelta(days=5)
            continue
        if t.startswith("latitude"):
            df = pd.read_csv(io.StringIO(t))
            if len(df):
                df["source"] = s
                df.to_csv(out, mode="a", header=not os.path.exists(out), index=False)
                n += len(df)
        else:
            print(s, d, t[:80], flush=True)
        d += dt.timedelta(days=5)
    print(s, "rows", n, flush=True)
