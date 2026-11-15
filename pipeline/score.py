"""Score the radar change against the optical burn map, from the same files the page reads.

Usage: uv run python pipeline/score.py

For every window and track it scores placebo pairs (two passes before the fire season, where nothing should
show) and fire pairs (the baseline pass against each later pass), on about 200 m cells:
  AUC         chance that a random burned cell lost more backscatter than a random unburned cell (0.5 is no signal)
  interval    95% interval of the AUC from resampling 2 km blocks of cells (neighbouring cells are not independent)
  rule        "HV fell by 1 dB or more", fixed before scoring: precision, false-alarm rate, recall, the share of
              flagged cells the optical map can judge at all, and the precision a random rule would get
Burned and unburned come from HLS dNBR (above 0.27, below 0.10). Cells in between, and cells with no clear
optical view, are left out. Writes docs/data/scores.json and prints a table.
"""
import json
import numpy as np, pandas as pd
from config import ROOT, SITE_DATA, HV_RULE_DB, HEADLINE_LAST, BOOT_BLOCK, BOOT_REPS, BOOT_SEED


def auc(pos, neg):
    if len(pos) < 5 or len(neg) < 5:
        return None
    r = pd.Series(np.concatenate([pos, neg])).rank().values
    # 6 decimals so the two-decimal README table rounds once, like the page (0.79497 is 0.79, not 0.795 then 0.80)
    return round(float((r[:len(pos)].sum() - len(pos) * (len(pos) + 1) / 2) / (len(pos) * len(neg))), 6)


def auc_fast(pos, neg):
    """Same number as auc() (ties count half), without the rounding and the size check. Used for resampling."""
    s = np.sort(neg)
    less, le = np.searchsorted(s, pos, "left"), np.searchsorted(s, pos, "right")
    return float((less + 0.5 * (le - less)).sum() / (len(pos) * len(neg)))


def auc_interval(pos, neg, pos_blk, neg_blk, nblocks, rng, reps=BOOT_REPS):
    """95% interval of the AUC. Whole blocks of cells are drawn with replacement, so cells that sit next to
    each other stay together. pos_blk and neg_blk give the block number of every value."""
    if len(pos) < 5 or len(neg) < 5:
        return None
    out = []
    for _ in range(reps):
        w = np.bincount(rng.integers(0, nblocks, nblocks), minlength=nblocks)
        p, q = np.repeat(pos, w[pos_blk]), np.repeat(neg, w[neg_blk])
        if len(p) and len(q):
            out.append(auc_fast(p, q))
    lo, hi = np.percentile(out, [2.5, 97.5])
    return [round(float(lo), 3), round(float(hi), 3)]


def score_pair(a, b, lab, nodata, rule, blk=None, rng=None):
    """a, b: (2, n, n) int arrays (dB x 100) for HV and HH on two dates. Returns the numbers for the pair.
    blk: (n, n) block number of every cell; with rng it adds the block-resampled interval of each AUC."""
    out = {}
    for j, pol in enumerate(("hv", "hh")):
        ok = (a[j] != nodata) & (b[j] != nodata)
        ch = b[j].astype("int32") - a[j].astype("int32")
        burned, severe, unb = ok & (lab >= 3), ok & (lab == 4), ok & (lab == 1)
        out[pol + "_auc"] = auc(-ch[burned], -ch[unb])
        if blk is not None:
            out[pol + "_auc_ci"] = auc_interval(-ch[burned], -ch[unb], blk[burned], blk[unb], int(blk.max()) + 1, rng)
        out[pol + "_auc_severe"] = auc(-ch[severe], -ch[unb])
        out[pol + "_median_burned"] = round(float(np.median(ch[burned])) / 100, 2)
        out[pol + "_median_unburned"] = round(float(np.median(ch[unb])) / 100, 2)
        flag = ok & (ch <= rule)
        tp, fp = int((flag & burned).sum()), int((flag & unb).sum())
        nb, nu, nf = int(burned.sum()), int(unb.sum()), int(flag.sum())
        out[pol + "_rule"] = {"flagged": nf, "flagged_burned": tp, "flagged_unburned": fp,
                              "precision": round(tp / (tp + fp), 3) if tp + fp else None,
                              "false_alarm": round(fp / max(nu, 1), 3),
                              "recall": round(tp / max(nb, 1), 3),
                              # share of the flagged cells that the optical map labels burned or unburned at all
                              "scored_share": round((tp + fp) / nf, 3) if nf else None,
                              # precision of a rule that flags cells at random: burned share of the scored cells
                              "base_rate": round(nb / (nb + nu), 3) if nb + nu else None}
    return out


def main():
    meta = json.load(open(SITE_DATA / "meta.json"))
    n = meta["ncell"]
    rule = round(HV_RULE_DB * meta["cell_scale"])   # the page (docs/score.js) works on the same integers, dB x 100
    nodata = meta["cell_nodata"]
    side = -(-n // BOOT_BLOCK)
    blk = (np.arange(n)[:, None] // BOOT_BLOCK) * side + np.arange(n)[None, :] // BOOT_BLOCK
    rng = np.random.default_rng(BOOT_SEED)

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
                                     **score_pair(c[dates.index(a)], c[dates.index(b)], lab, nodata, rule, blk, rng)})
            res.append(rec)
            print(f"scored {w} track {tr}", flush=True)

    json.dump(res, open(SITE_DATA / "scores.json", "w"), indent=1)

    # README table: placebo pairs next to the headline fire-season pair (the last pass up to HEADLINE_LAST).
    months = "Jan Feb Mar Apr May Jun Jul Aug Sep Oct Nov Dec".split()
    day = lambda d: f"{int(d[8:])} {months[int(d[5:7]) - 1]}"
    pc = lambda v, dp=0: "n/a" if v is None else f"{v * 100:.{dp}f}%"
    ci = lambda v: "" if v is None else f" ({v[0]:.2f} to {v[1]:.2f})"
    rows = ["| Window, track | HV AUC on placebo pairs | Fire-season pair | HV AUC (95% interval) | Rule right when it fires "
            "| Right by chance | Flagged cells the optical map can judge | Rule false alarms | Burned cells caught | HH AUC |",
            "|---|---|---|---|---|---|---|---|---|---|"]
    for rec in res:
        placebo = ", ".join(f"{p['hv_auc']:.2f}" for p in rec["pairs"] if p["kind"] == "placebo")
        fires = [p for p in rec["pairs"] if p["kind"] == "fire" and p["to"] <= HEADLINE_LAST]
        if not fires:
            continue
        fire = fires[-1]
        r = fire["hv_rule"]
        judged = r["flagged_burned"] + r["flagged_unburned"]
        rows.append(f"| {rec['window'][1:]}, {rec['track']} | {placebo} | {day(fire['from'])} to {day(fire['to'])} 2026 | "
                    f"{fire['hv_auc']:.2f}{ci(fire['hv_auc_ci'])} | {pc(r['precision'])} ({r['flagged_burned']} of {judged}) | "
                    f"{pc(r['base_rate'])} | {judged} of {r['flagged']} ({pc(r['scored_share'])}) | "
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
            print(f"  {p['kind']:7s} {p['from']} to {p['to']}: HV AUC {p['hv_auc']} {p['hv_auc_ci']} (severe {p['hv_auc_severe']}), "
                  f"median {p['hv_median_burned']}/{p['hv_median_unburned']} dB | HH AUC {p['hh_auc']} | "
                  f"rule: precision {r['precision']} (chance {r['base_rate']}) false alarm {r['false_alarm']} recall {r['recall']}")


if __name__ == "__main__":
    main()
