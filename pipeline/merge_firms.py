"""Merge the later FIRMS pulls (windows 3 to 6, added 2026-11-15) into data/firms/hotspots.csv.

Usage: uv run python pipeline/merge_firms.py
The first pull is kept as data/firms/hotspots_w12.csv. The two boxes overlap, so rows are de-duplicated on
position, time and source. Windows 1 and 2 must get the same hotspot counts as before; build_site.py prints them.
"""
import pandas as pd
from config import DATA

d = DATA / "firms"
first = d / "hotspots_w12.csv"
if not first.exists():
    (d / "hotspots.csv").rename(first)
a = pd.read_csv(first, low_memory=False)
extra = sorted(p for p in d.glob("hotspots_*.csv") if p.name != "hotspots_w12.csv")
b = pd.concat([pd.read_csv(p, low_memory=False) for p in extra], ignore_index=True)
key = ["latitude", "longitude", "acq_date", "acq_time", "source"]
m = pd.concat([a, b], ignore_index=True).drop_duplicates(subset=key)
m.to_csv(d / "hotspots.csv", index=False)
print(f"first pull {len(a)}, later pulls {len(b)} from {[p.name for p in extra]}, merged {len(m)}")
