"""Write the Indonesia outline the deck's map slide draws (docs/deck/land.svg).

Usage: uv run python pipeline/deck_map.py path/to/ne_50m_land.geojson
Source: Natural Earth 1:50m land polygons (public domain),
https://raw.githubusercontent.com/nvkelso/natural-earth-vector/master/geojson/ne_50m_land.geojson
Plain lon/lat projection; the viewBox crops to the region, so polygons are not clipped.
"""
import json, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
W, E, S, N = 94.0, 142.0, -11.0, 7.0
K = 24.0  # pixels per degree


def xy(lon, lat):
    return (lon - W) * K, (N - lat) * K


def ring_path(ring):
    pts = [xy(*p[:2]) for p in ring]
    keep = [pts[0]]
    for p in pts[1:]:
        if abs(p[0] - keep[-1][0]) + abs(p[1] - keep[-1][1]) >= 0.8:
            keep.append(p)
    if len(keep) < 4:
        return ""
    return "M" + "L".join(f"{x:.1f} {y:.1f}" for x, y in keep) + "Z"


gj = json.load(open(sys.argv[1], encoding="utf-8"))
parts = []
for f in gj["features"]:
    g = f["geometry"]
    polys = g["coordinates"] if g["type"] == "MultiPolygon" else [g["coordinates"]]
    for poly in polys:
        outer = poly[0]
        lons = [p[0] for p in outer]
        lats = [p[1] for p in outer]
        if max(lons) < W or min(lons) > E or max(lats) < S or min(lats) > N:
            continue
        parts.append(ring_path(outer))
d = "".join(p for p in parts if p)
w, h = (E - W) * K, (N - S) * K
svg = (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {w:.0f} {h:.0f}">'
       f'<path d="{d}"/></svg>')
(ROOT / "docs" / "deck" / "land.svg").write_text(svg, encoding="utf-8")
print("polygons:", len(parts), "bytes:", len(svg), "size:", w, h)
