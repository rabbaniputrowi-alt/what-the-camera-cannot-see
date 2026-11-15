"""List the NISAR GCOV scenes over the study windows. No login needed.

Usage: uv run python pipeline/search.py
Searches each window box in config.WINDOWS and keeps a scene only if its footprint contains the whole box,
so a window is never cut by a frame edge. Writes data/gcov_scenes.json (date, track, direction, URL and the
windows each scene contains) and prints one line per scene.
"""
import json
import asf_search as asf
from shapely.geometry import box, shape
from config import DATA, WINDOWS

KEEP = ["sceneName", "startTime", "pathNumber", "frameNumber", "flightDirection", "bytes", "browse", "url",
        "fileID", "collectionName"]

rows = {}
for w, wc in WINDOWS.items():
    b = box(*wc["bbox"])
    for r in asf.search(dataset="NISAR", processingLevel="GCOV", intersectsWith=b.wkt, maxResults=500):
        if not shape(r.geometry).contains(b):
            continue
        row = rows.setdefault(r.properties["sceneName"], {k: r.properties.get(k) for k in KEEP})
        row["polygon"] = r.geometry
        row.setdefault("windows", [])
        if w not in row["windows"]:
            row["windows"].append(w)
rows = sorted(rows.values(), key=lambda x: x["startTime"])
# A scene can be listed twice in two processing versions (for example ..._001 and ..._002 on 4 Sep, track 155).
# Keep the newest version per track and start time.
newest = {}
for x in rows:
    k = (x["pathNumber"], x["startTime"])
    if k not in newest or x["sceneName"] > newest[k]["sceneName"]:
        newest[k] = x
rows = sorted(newest.values(), key=lambda x: x["startTime"])
DATA.mkdir(exist_ok=True)
json.dump(rows, open(DATA / "gcov_scenes.json", "w"), indent=1, default=str)
for x in rows:
    print(x["startTime"][:10], x["pathNumber"], x["flightDirection"], ",".join(x["windows"]), x["sceneName"])
print(len(rows), "scenes")
