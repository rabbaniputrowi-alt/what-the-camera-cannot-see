"""Shared settings for the pipeline. Every number that shapes a result lives here."""
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data"
WIN_DIR = DATA / "win"
SITE = ROOT / "docs"
SITE_DATA = SITE / "data"

# Study windows as lon/lat boxes (west, south, east, north), about 22 km on a side.
WINDOWS = {
    "w1": {"bbox": (113.95, -2.85, 114.15, -2.65), "label": "Window 1, Pulang Pisau canal blocks"},
    "w2": {"bbox": (113.70, -2.40, 113.90, -2.20), "label": "Window 2, 50 km north-west"},
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
