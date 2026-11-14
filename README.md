# What the camera cannot see

NISAR L-band radar over the 2026 peat fires in Pulang Pisau, Central Kalimantan, Indonesia.
NASA Space Apps Challenge 2026, challenge "Dancing with the SARs", Jakarta local event.

> PLACEHOLDER (idea statement): Rabbani's own words go here.

## What this is

A static web page with a before and after slider over two 22 km windows of peatland. It shows NISAR radar
backscatter on any two of the available dates, with four layers that can be switched on: the change between
the two dates, a fixed detection rule, the VIIRS fire hotspots between the two dates, and an optical burn map
from Landsat and Sentinel-2. The page scores the radar change against the optical burn map for whichever pair
is selected, including placebo pairs from before the fire season.

The page is in `docs/` and needs no server code and no external requests. The Python scripts in `pipeline/`
build every file it reads from open NASA data.

## What it shows so far

Scored on cells of about 200 m against the optical burn map (HLS dNBR above 0.27 is burned, below 0.10 is
unburned, cells in between and cells with no clear optical view are left out). AUC is the chance that a
burned cell lost more backscatter than an unburned one; 0.50 means no signal. The rule "HV fell by 1 dB or
more" was fixed before scoring. Full numbers for every pair: `docs/data/scores.json`.

<!-- results:start (written by pipeline/score.py, do not edit by hand) -->
| Window, track | HV AUC on placebo pairs | Fire-season pair | HV AUC | Rule right when it fires | Rule false alarms | Burned cells caught | HH AUC |
|---|---|---|---|---|---|---|---|
| 1, 125 | 0.51, 0.45 | 16 Jul to 20 Oct 2026 | 0.81 | 95% (946 of 998) | 2.7% | 32% | 0.60 |
| 1, 61 | 0.50, 0.46, 0.49 | 24 Jul to 16 Oct 2026 | 0.73 | 96% (673 of 700) | 1.4% | 22% | 0.55 |
| 2, 125 | 0.45, 0.71 | 16 Jul to 20 Oct 2026 | 0.91 | 82% (321 of 391) | 2.5% | 74% | 0.55 |
| 2, 61 | 0.77, 0.69, 0.61 | 24 Jul to 16 Oct 2026 | 0.88 | 88% (202 of 230) | 1.0% | 46% | 0.36 |
<!-- results:end -->

HH shows no comparable signal: its fire-season AUC stays in the range of its own placebo pairs.

## Limits

- Two windows of about 22 km, two orbits, one fire season. This is not a burned-area product.
- The optical map used as truth is itself read through smoke (pixels that HLS flags as high aerosol are kept,
  because the flag covers the whole window on the fire-season passes). Some optical burn may be haze.
- Large parts of both windows have no clear optical pixel after the fires and are not scored.
- The 1 dB rule finds the strongly changed core of the burn, not all of it. It is not tuned or cross-validated.
- In window 2 the placebo test fails on some pairs: before the fires, cells that later burned were already
  losing HV (AUC up to 0.77), and the burned sample is small. Window 1 is the clean case.
- Most radar scenes are provisional releases. Scores use no speckle filter beyond averaging to 200 m.
- Radar change is not fire by itself: water level, rain and land clearing change the echo too.
- The camera did see the ground on some days: in August and early September, and on 4 October through smoke
  plumes. The optical images on the page are surface reflectance, already corrected for the atmosphere.

## Rebuild it

Needs [uv](https://docs.astral.sh/uv/), a free NASA Earthdata login token and a free FIRMS map key.

```
cp .env.example .env            # then paste your EDL_TOKEN and FIRMS_MAP_KEY into .env
uv sync
uv run python pipeline/search.py                 # list the NISAR GCOV scenes (no login)
uv run python pipeline/stream.py --track 125     # stream the two windows from each scene, about 2 min each
uv run python pipeline/stream.py --track 61
uv run python pipeline/firms_pull.py             # VIIRS and MODIS hotspots
uv run python pipeline/hls_dnbr.py w1            # optical burn map, about 5 min per window
uv run python pipeline/hls_dnbr.py w2
uv run python pipeline/build_site.py             # images, 200 m cells, labels, overlays, meta.json
uv run python pipeline/score.py                  # docs/data/scores.json and a printed table
node tests/check_scores.cjs                      # the page's scoring equals the pipeline's
python -m http.server 8765 --directory docs      # open http://127.0.0.1:8765/
```

Raw data stays out of the repository (`data/` is ignored). `docs/data/` holds only the derived files the
page reads. Every threshold and grid size is in `pipeline/config.py`.

## Data

NISAR L2 GCOV from the Alaska Satellite Facility DAAC, VIIRS active fire detections from NASA FIRMS, and
Harmonized Landsat and Sentinel-2 (HLS) v2.0 from NASA LP DAAC. Full list with links and DOIs:
[REFERENCES.md](REFERENCES.md).

This project is not endorsed by NASA and uses no NASA logos or mission identifiers.

## AI use

> PLACEHOLDER (AI statement): Rabbani's statement on how AI tools were used goes here.

## Licence

MIT, see [LICENSE](LICENSE).
