"""Shared settings for the pipeline. Every number that shapes a result lives here."""
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data"
WIN_DIR = DATA / "win"
SITE = ROOT / "docs"
SITE_DATA = SITE / "data"

# Study windows as lon/lat boxes (west, south, east, north), about 22 km on a side.
WINDOWS = {
    "w1": {"bbox": (113.95, -2.85, 114.15, -2.65), "label": "Window 1, Pulang Pisau canal blocks",
           # what the eye sees on the peak passes that the cloud mask rejects (every thumbnail was looked at)
           "pass_note": "The mask is strict. By eye, two more peak passes show part of the ground: 16 Sep "
                        "through thin smoke and 31 Oct between clouds."},
    "w2": {"bbox": (113.70, -2.40, 113.90, -2.20), "label": "Window 2, 50 km north-west",
           "pass_note": "The mask is strict. By eye, two more peak passes show part of the ground: 18 Sep "
                        "between clouds and 19 Sep through smoke."},
}

# NISAR tracks over both windows. Each has its own look direction and UTM grid.
TRACKS = {
    125: {"direction": "ascending", "epsg": 32750},
    61: {"direction": "descending", "epsg": 32749},
}

# Baseline (last pass before the fire season) and the pre-season passes used for placebo pairs.
BASELINE = {125: "2026-07-16", 61: "2026-07-24"}
PRE_SEASON_END = "2026-07-31"

# Scoring grid: about 200 m cells (CELL_PX display pixels on a side, see below).

# Optical truth (HLS dNBR) cuts, the usual severity classes.
DNBR_BURNED = 0.27
DNBR_SEVERE = 0.44
DNBR_UNBURNED = 0.10

# The fixed rule, chosen before scoring: HV backscatter fell by 1 dB or more.
HV_RULE_DB = -1.0

# The fixed rule for counting a "usable look" by an optical satellite, chosen before counting:
# the pass covers at least 90% of the window and HLS's own mask calls less than half of that cloud.
USABLE_COVER = 0.90
USABLE_CLOUD = 0.50
# Periods for the pass count. The peak boundary (15 Sep) was set after looking at the window 1 images,
# so all three periods are always shown together.
PERIODS = [("2026-06-10", "2026-07-31", "Before the fires"),
           ("2026-08-01", "2026-09-14", "First fires"),
           ("2026-09-15", "2026-11-01", "Peak of the fires")]
THUMB_PX = 148               # radar thumbnails for the pass strip

# Display grid: every layer is resampled to the same lon/lat grid per window.
DISPLAY_PX = 1110            # about 20 m per pixel
CELL_PX = 10                 # scoring cells are 10 by 10 display pixels, about 200 m
SPECKLE_BOX = 3              # mean filter (in linear power) applied to the display images only
HV_STRETCH_DB = (-20.0, -7.0)
HH_STRETCH_DB = (-14.0, -2.0)


def win_path(window: str, track: int, date: str) -> Path:
    return WIN_DIR / f"{window}_t{track}_{date}.npz"


def dates_on_disk(window: str, track: int) -> list[str]:
    return sorted(p.stem.split("_")[-1] for p in WIN_DIR.glob(f"{window}_t{track}_*.npz")
                  if ".part" not in p.name)
