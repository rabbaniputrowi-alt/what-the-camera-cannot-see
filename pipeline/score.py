"""Score the radar change against the optical burn map, from the same files the page reads.

Usage: uv run python pipeline/score.py

For every window and track it scores placebo pairs (two passes before the fire season, where nothing should
show) and fire pairs (the baseline pass against each later pass), on about 200 m cells:
  AUC         chance that a random burned cell lost more backscatter than a random unburned cell (0.5 is no signal)
  rule        "HV fell by 1 dB or more", fixed before scoring: precision, false-alarm rate, recall
Burned and unburned come from HLS dNBR (above 0.27, below 0.10). Cells in between, and cells with no clear
optical view, are left out. Writes docs/data/scores.json and prints a table.
"""
import json
import numpy as np, pandas as pd
from config import ROOT, SITE_DATA, HV_RULE_DB

meta = json.load(open(SITE_DATA / "meta.json"))
n = meta["ncell"]
RULE = round(HV_RULE_DB * meta["cell_scale"])   # the page (docs/score.js) works on the same integers, dB x 100


def auc(pos, neg):
    if len(pos) < 5 or len(neg) < 5:
        return None
    r = pd.Series(np.concatenate([pos, neg])).rank().values
    return round(float((r[:len(pos)].sum() - len(pos) * (len(pos) + 1) / 2) / (len(pos) * len(neg))), 3)


def score_pair(a, b, lab):
    """a, b: (2, n, n) int arrays (dB x 100) for HV and HH on two dates. Returns the numbers for the pair."""
    out = {}
    for j, pol in enumerate(("hv", "hh")):
        ok = (a[j] != meta["cell_nodata"]) & (b[j] != meta["cell_nodata"])
        ch = b[j].astype("int32") - a[j].astype("int32")
        burned, severe, unb = ok & (lab >= 3), ok & (lab == 4), ok & (lab == 1)
        out[pol + "_auc"] = auc(-ch[burned], -ch[unb])
        out[pol + "_auc_severe"] = auc(-ch[severe], -ch[unb])
        out[pol + "_median_burned"] = round(float(np.median(ch[burned])) / 100, 2)
        out[pol + "_median_unburned"] = round(float(np.median(ch[unb])) / 100, 2)
        flag = ok & (ch <= RULE)
        tp, fp = int((flag & burned).sum()), int((flag & unb).sum())
        out[pol + "_rule"] = {"flagged": int(flag.sum()), "flagged_burned": tp, "flagged_unburned": fp,
                              "precision": round(tp / (tp + fp), 3) if tp + fp else None,
                              "false_alarm": round(fp / max(int(unb.sum()), 1), 3),
                              "recall": round(tp / max(int(burned.sum()), 1), 3)}
    return out


res = []
for w, wm in meta["windows"].items():
    lab = np.fromfile(SITE_DATA / wm["optical"]["labels"], "uint8").reshape(n, n)
    for tr, tm in wm["tracks"].items():
        dates = tm["dates"]
        c = np.fromfile(SITE_DATA / tm["cells"], "<i2").reshape(len(dates), 2, n, n)
        pre = tm["pre_season"]
        pairs = [(a, b, "placebo") for a, b in zip(pre[:-1], pre[1:])]
        pairs += [(tm["baseline"], d, "fire") for d in dates if d > tm["baseline"]]
        rec = {"window": w, "track": int(tr), "burned_cells": int((lab >= 3).sum()),
               "severe_cells": int((lab == 4).sum()), "unburned_cells": int((lab == 1).sum()), "pairs": []}
        for a, b, kind in pairs:
            rec["pairs"].append({"from": a, "to": b, "kind": kind,
                                 **score_pair(c[dates.index(a)], c[dates.index(b)], lab)})
        res.append(rec)

json.dump(res, open(SITE_DATA / "scores.json", "w"), indent=1)

# README table: placebo pairs next to the headline fire-season pair (the last pass up to 25 October).
MONTHS = "Jan Feb Mar Apr May Jun Jul Aug Sep Oct Nov Dec".split()
day = lambda d: f"{int(d[8:])} {MONTHS[int(d[5:7]) - 1]}"
pc = lambda v, dp=0: "n/a" if v is None else f"{v * 100:.{dp}f}%"
rows = ["| Window, track | HV AUC on placebo pairs | Fire-season pair | HV AUC | Rule right when it fires | Rule false alarms | Burned cells caught | HH AUC |",
        "|---|---|---|---|---|---|---|---|"]
for rec in res:
    placebo = ", ".join(f"{p['hv_auc']:.2f}" for p in rec["pairs"] if p["kind"] == "placebo")
    fire = [p for p in rec["pairs"] if p["kind"] == "fire" and p["to"] <= "2026-10-25"][-1]
    r = fire["hv_rule"]
    rows.append(f"| {rec['window'][1:]}, {rec['track']} | {placebo} | {day(fire['from'])} to {day(fire['to'])} 2026 | "
                f"{fire['hv_auc']:.2f} | {pc(r['precision'])} ({r['flagged_burned']} of {r['flagged_burned'] + r['flagged_unburned']}) | "
                f"{pc(r['false_alarm'], 1)} | {pc(r['recall'])} | {fire['hh_auc']:.2f} |")
readme = (ROOT / "README.md").read_text(encoding="utf-8")
head, rest = readme.split("<!-- results:start", 1)
marker, tail = rest.split("-->", 1)[0], rest.split("<!-- results:end -->", 1)[1]
(ROOT / "README.md").write_text(head + "<!-- results:start" + marker + "-->\n" + "\n".join(rows) + "\n<!-- results:end -->" + tail,
                                encoding="utf-8", newline="\n")
for rec in res:
    print(f"\n== {rec['window']} track {rec['track']}: burned {rec['burned_cells']} (severe {rec['severe_cells']}), "
          f"unburned {rec['unburned_cells']}")
    for p in rec["pairs"]:
        r = p["hv_rule"]
        print(f"  {p['kind']:7s} {p['from']} to {p['to']}: HV AUC {p['hv_auc']} (severe {p['hv_auc_severe']}), "
              f"median {p['hv_median_burned']}/{p['hv_median_unburned']} dB | HH AUC {p['hh_auc']} | "
              f"rule: precision {r['precision']} false alarm {r['false_alarm']} recall {r['recall']}")
