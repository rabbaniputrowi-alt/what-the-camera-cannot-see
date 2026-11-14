"""List the NISAR GCOV scenes over the study area. No login needed.

Usage: uv run python pipeline/search.py
Writes data/gcov_scenes.json (date, track, direction, URL per scene) and prints one line per scene.
"""
import json
import asf_search as asf
from config import DATA

AOI = "POINT(114.05 -2.75)"   # inside window 1; both tracks that cover it also cover window 2
KEEP = ["sceneName", "startTime", "pathNumber", "frameNumber", "flightDirection", "bytes", "browse", "url",
        "fileID", "collectionName"]

rows = []
for r in asf.search(dataset="NISAR", processingLevel="GCOV", intersectsWith=AOI, maxResults=200):
    row = {k: r.properties.get(k) for k in KEEP}
    row["polygon"] = r.geometry
    rows.append(row)
rows.sort(key=lambda x: x["startTime"])
DATA.mkdir(exist_ok=True)
json.dump(rows, open(DATA / "gcov_scenes.json", "w"), indent=1, default=str)
for x in rows:
    print(x["startTime"][:10], x["pathNumber"], x["flightDirection"], x["collectionName"], x["sceneName"])
print(len(rows), "scenes")
