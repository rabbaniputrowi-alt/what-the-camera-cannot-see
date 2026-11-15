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
    # Added 2026-11-15 to widen the scope beyond Pulang Pisau. Picked as the densest 0.2 degree boxes of
    # NOAA-20 VIIRS detections (17 Jul to 1 Nov) that do not overlap w1 or w2; both tracks cover them fully.
    "w3": {"bbox": (114.30, -2.55, 114.50, -2.35), "label": "Window 3, Kapuas, 50 km north-east",
           "pass_note": ""},
    "w4": {"bbox": (112.80, -2.95, 113.00, -2.75), "label": "Window 4, Kotawaringin Timur, 130 km west",
           "pass_note": ""},
    # Further out, same selection rule inside a 1.4 degree box around each regency's fire cluster.
    "w5": {"bbox": (110.10, -1.90, 110.30, -1.70), "label": "Window 5, Ketapang, West Kalimantan",
           "pass_note": "", "tracks": [90, 155]},
    "w6": {"bbox": (105.10, -3.45, 105.30, -3.25), "label": "Window 6, Ogan Komering Ilir, South Sumatra",
           "pass_note": "", "tracks": [10, 119]},
    "w7": {"bbox": (103.80, -1.95, 104.00, -1.75), "label": "Window 7, Bayung Lencir, South Sumatra and Jambi border",
           "pass_note": "", "tracks": [47, 112]},
    "w8": {"bbox": (140.55, -7.95, 140.75, -7.75), "label": "Window 8, Merauke, South Papua (savanna, not peat)",
           "pass_note": "", "tracks": [132, 124]},
}
# Windows without a "tracks" entry use tracks 125 and 61. The first track listed sets the optical grid.
DEFAULT_TRACKS = [125, 61]


def window_tracks(w: str) -> list[int]:
    return WINDOWS[w].get("tracks", DEFAULT_TRACKS)


# NISAR tracks. Each has its own look direction and UTM grid.
TRACKS = {
    125: {"direction": "ascending", "epsg": 32750},
    61: {"direction": "descending", "epsg": 32749},
    155: {"direction": "ascending", "epsg": 32749},
    90: {"direction": "descending", "epsg": 32749},
    10: {"direction": "ascending", "epsg": 32748},
    119: {"direction": "descending", "epsg": 32748},
    112: {"direction": "ascending", "epsg": 32748},
    47: {"direction": "descending", "epsg": 32748},
    124: {"direction": "ascending", "epsg": 32754},
    132: {"direction": "descending", "epsg": 32754},
}

# Baseline (last pass before the fire season) and the pre-season passes used for placebo pairs.
# For the tracks added on 2026-11-15 the baseline is the last pass before 31 July, the same rule as before.
BASELINE = {125: "2026-07-16", 61: "2026-07-24", 155: "2026-07-18", 90: "2026-07-26", 10: "2026-07-20",
            119: "2026-07-16", 47: "2026-07-23", 112: "2026-07-15", 124: "2026-07-04", 132: "2026-07-17"}
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
