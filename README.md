# What the camera cannot see

NISAR L-band radar over the 2026 fire season in Indonesia: eight windows of about 22 km, starting from the peat
fires in Pulang Pisau, Central Kalimantan, and reaching West Kalimantan, South Sumatra and South Papua.
NASA Space Apps Challenge 2026, challenge "Dancing with the SARs", Jakarta local event.

> PLACEHOLDER (idea statement): Rabbani's own words go here.

## What this is

A static web page with a before and after slider over eight 22 km windows: seven on peatland in Kalimantan and
Sumatra and one on savanna in South Papua. It shows NISAR radar
backscatter on any two of the available dates, with four layers that can be switched on: the change between
the two dates, a fixed detection rule, the VIIRS fire hotspots between the two dates, and an optical burn map
from Landsat and Sentinel-2. The page scores the radar change against the optical burn map for whichever pair
is selected, including placebo pairs from before the fire season.

A seven-slide demo deck is in `docs/deck/` (arrow keys to move). The page is in `docs/` and needs no server code and no external requests. The Python scripts in `pipeline/`
build every file it reads from open NASA data.

## What it shows so far

Scored on cells of about 200 m against the optical burn map (HLS dNBR above 0.27 is burned, below 0.10 is
unburned, cells in between and cells with no clear optical view are left out). AUC is the chance that a
burned cell lost more backscatter than an unburned one; 0.50 means no signal. The rule "HV fell by 1 dB or
more" was fixed before scoring. Full numbers for every pair: `docs/data/scores.json`.

How to read the columns:

- **HV AUC (95% interval).** Cells next to each other are not independent, so the interval comes from resampling
  2 km blocks of cells, not single cells. It covers sampling within the window only, not the choice of window,
  dates or thresholds.
- **Right by chance.** The share of scored cells that are burned, which is what a rule flagging cells at random
  would score. "Rule right when it fires" means something only against this number.
- **Flagged cells the optical map can judge.** The rule also flags cells the optical map labels "in between"
  or cannot see. Those cells are in neither count, so "right when it fires" describes only the share shown here.
- **Fire-season pair.** The baseline against the last pass on or before 25 October. That date has been in the
  code since the first commit and its reason was not written down. Of the 14 tracks with a later pass, the AUC
  on that later pass is higher on 10, the same on 1 and lower on 3 (see Limits for the largest fall).

<!-- results:start (written by pipeline/score.py, do not edit by hand) -->
| Window, track | HV AUC on placebo pairs | Fire-season pair | HV AUC (95% interval) | Rule right when it fires | Right by chance | Flagged cells the optical map can judge | Rule false alarms | Burned cells caught | HH AUC |
|---|---|---|---|---|---|---|---|---|---|
| 1, 125 | 0.51, 0.45 | 16 Jul to 20 Oct 2026 | 0.81 (0.75 to 0.87) | 95% (946 of 998) | 61% | 998 of 1701 (59%) | 2.7% | 32% | 0.61 |
| 1, 61 | 0.50, 0.46, 0.49 | 24 Jul to 16 Oct 2026 | 0.73 (0.63 to 0.80) | 96% (673 of 700) | 61% | 700 of 857 (82%) | 1.4% | 22% | 0.54 |
| 2, 125 | 0.45, 0.71 | 16 Jul to 20 Oct 2026 | 0.91 (0.80 to 0.98) | 82% (321 of 391) | 14% | 391 of 2148 (18%) | 2.5% | 74% | 0.55 |
| 2, 61 | 0.77, 0.70, 0.61 | 24 Jul to 16 Oct 2026 | 0.88 (0.79 to 0.96) | 88% (202 of 230) | 14% | 230 of 1570 (15%) | 1.0% | 46% | 0.36 |
| 3, 125 | 0.51, 0.57 | 16 Jul to 20 Oct 2026 | 0.79 (0.74 to 0.86) | 80% (338 of 422) | 43% | 422 of 1216 (35%) | 7.6% | 41% | 0.58 |
| 3, 61 | 0.68, 0.46, 0.52 | 24 Jul to 16 Oct 2026 | 0.79 (0.72 to 0.85) | 88% (207 of 236) | 43% | 236 of 434 (54%) | 2.6% | 25% | 0.58 |
| 4, 125 | 0.41, 0.34 | 16 Jul to 20 Oct 2026 | 0.76 (0.71 to 0.82) | 96% (2259 of 2342) | 68% | 2342 of 3305 (71%) | 4.2% | 55% | 0.48 |
| 4, 61 | 0.64, 0.48, 0.49 | 24 Jul to 16 Oct 2026 | 0.60 (0.54 to 0.65) | 85% (1918 of 2262) | 68% | 2262 of 3489 (65%) | 17.4% | 47% | 0.25 |
| 5, 155 | 0.47, 0.33 | 18 Jul to 22 Oct 2026 | 0.78 (0.74 to 0.82) | 70% (3799 of 5444) | 51% | 5444 of 6448 (84%) | 33.6% | 76% | 0.31 |
| 5, 90 | 0.35, 0.26, 0.50 | 26 Jul to 18 Oct 2026 | 0.81 (0.76 to 0.85) | 90% (2650 of 2936) | 51% | 2936 of 3445 (85%) | 5.8% | 53% | 0.41 |
| 6, 10 | 0.45, 0.50 | 20 Jul to 24 Oct 2026 | 0.68 (0.63 to 0.73) | 89% (1575 of 1775) | 69% | 1775 of 2909 (61%) | 10.5% | 38% | 0.45 |
| 6, 119 | 0.33, 0.39 | 16 Jul to 20 Oct 2026 | 0.55 (0.49 to 0.61) | 91% (498 of 549) | 69% | 549 of 949 (58%) | 2.7% | 12% | 0.32 |
| 7, 112 | 0.49, 0.31 | 15 Jul to 19 Oct 2026 | 0.76 (0.64 to 0.86) | 23% (255 of 1089) | 12% | 1089 of 4861 (22%) | 31.9% | 71% | 0.43 |
| 7, 47 | 0.63, 0.32, 0.41 | 23 Jul to 15 Oct 2026 | 0.70 (0.58 to 0.82) | 37% (212 of 574) | 12% | 574 of 2654 (22%) | 13.8% | 59% | 0.41 |
| 8, 124 | 0.28 | 4 Jul to 20 Oct 2026 | 0.57 (0.50 to 0.64) | 52% (1346 of 2593) | 50% | 2593 of 8295 (31%) | 81.0% | 88% | 0.47 |
| 8, 132 | 0.07 | 17 Jul to 21 Oct 2026 | 0.65 (0.59 to 0.72) | 60% (877 of 1458) | 50% | 1458 of 4590 (32%) | 37.7% | 57% | 0.40 |
<!-- results:end -->

### Where it works and where it does not

- **Forested peat in Kalimantan (windows 1 to 5): the HV signal holds.** Fire-season HV AUC is 0.60 to 0.91 across
  both orbits: nine of the ten tracks are at 0.73 or above, and window 4 on track 61 is at 0.60. The 1 dB rule
  is right 80 to 96% of the time when it fires, except on the 20 m orbit over Ketapang (70%). A random rule
  would be right 14 to 68% of the time in these windows, so the gain is large in windows 2 and 3 and smaller
  in windows 1 and 4, where most scored cells are burned to begin with.
- **Peat in Sumatra (windows 6 and 7): weak.** In Ogan Komering Ilir the summary pairs give 0.68 and 0.55,
  and on track 10 the AUC stays at 0.51 to 0.56 until 12 October. Near Bayung Lencir the AUC is 0.70 to 0.76, but the rule is right only 23 to
  37% of the time, and very few cells are clear enough to score.
- **Savanna in South Papua (window 8): the method fails.** Placebo pairs reach 0.07 and 0.28 (far from 0.50),
  and the rule raises 38 to 81% false alarms. A likely reason, not tested, is that seasonal change in the grass swamps the burn signal.
- **Placebo pairs below 0.50** in windows 4 to 8 mean that ground which later burned was already changing
  differently from unburned ground before the fires. Window 1 is the cleanest case; window 3 has one placebo
  pair at 0.68.
- **HH does not show the burn as a loss of echo in any window.** Its fire-season AUC is 0.25 to 0.61 and never
  rises above its own placebo range. Where it moves (0.25 in window 4, 0.36 in window 2), burned ground got
  relatively brighter in HH, the opposite direction.

## What the camera saw

Every Landsat 8, Landsat 9 and Sentinel-2 pass over each window from 10 June to 13 November 2026 (HLS v2.0),
counted with a rule fixed before counting: a pass is a usable look when it covers at least 90% of the window
and HLS's own cloud mask (Fmask) calls less than half of the covered part cloud. Passes that cover less than
90% of a window (four over window 1, five over window 2) are left out of the count. Same-day Landsat and
Sentinel-2 passes count separately. NISAR passes are the scenes in the ASF archive over the same windows.

<!-- passes:start (written by pipeline/build_site.py, do not edit by hand) -->
| Window | Before the fires, 10 Jun to 31 Jul | First fires, 1 Aug to 14 Sep | Peak of the fires, 15 Sep to 1 Nov | NISAR passes with data, peak |
|---|---|---|---|---|
| Window 1, Pulang Pisau canal blocks | 11 of 17 | 13 of 16 | 1 of 11 (4 Oct) | 8 of 8 |
| Window 2, 50 km north-west | 18 of 26 | 18 of 25 | 1 of 15 (29 Oct) | 8 of 8 |
| Window 3, Kapuas, 50 km north-east | 10 of 17 | 13 of 17 | 2 of 13 (21 Sep, 1 Oct) | 8 of 8 |
| Window 4, Kotawaringin Timur, 130 km west | 13 of 19 | 8 of 14 | 6 of 13 | 8 of 8 |
| Window 5, Ketapang, West Kalimantan | 14 of 18 | 9 of 13 | 5 of 13 | 8 of 8 |
| Window 6, Ogan Komering Ilir, South Sumatra | 9 of 17 | 15 of 17 | 6 of 15 | 8 of 8 |
| Window 7, Bayung Lencir, South Sumatra and Jambi border | 6 of 12 | 13 of 16 | 2 of 11 (18 Sep, 19 Sep) | 8 of 8 |
| Window 8, Merauke, South Papua (savanna, not peat) | 8 of 15 | 9 of 16 | 12 of 17 | 6 of 8 |
<!-- passes:end -->

The mask is strict: looking at every image, two more peak passes per window show part of the ground through
thin smoke or between clouds. The start of the peak period (15 September) was chosen after looking at the
images, which is why all three periods are listed. Every image is on the page.

## Limits

- Eight windows of about 22 km, two orbits each, one fire season. This is not a burned-area product. Windows 1
  and 2 were chosen first. Windows 3 to 8 were added on 15 November 2026, each as the densest 0.2 degree box of
  NOAA-20 VIIRS detections (17 Jul to 1 Nov) in its area that does not overlap another window.
  The code that picked them is not in the repository.
- The optical burn map is the truth here, so the radar is scored on how well it agrees with what the camera
  saw. Where the camera saw nothing, the radar is not scored at all.
- The placebo pairs are 12 days apart and the fire-season pairs are about three months apart. The placebo
  shows what 12 days of ordinary change look like, not three months of it, so it does not rule out a seasonal
  difference between ground that burned and ground that did not. No fire-free year of NISAR data was used.
- The burn map covers the whole season (July against 1 October to 13 November). A pair that ends in August or
  September is scored against burns that had not all happened yet, so low early AUCs can be fire timing
  and not a weak signal.
- Window 2 on track 61 falls from 0.88 on 16 October to 0.49 on 28 October. The 28 October pass is the one
  from the validated collection. The cause was not investigated, and the table shows the 16 October pair.
- Over Merauke on track 132 the single placebo pair has an AUC of 0.07 and the rule flags 97% of unburned
  cells. A number that extreme may be a problem with one pass and not the season. It was not investigated.
- The optical map used as truth is itself read through smoke (pixels that HLS flags as high aerosol are kept,
  because the flag covers the whole window on the fire-season passes). Some optical burn may be haze.
- Large parts of windows 1, 2, 7 and 8 have no clear optical pixel and are not scored (clear share 0.34 to 0.59).
- For windows 7 and 8 the July optical composite was too cloudy under the first rule (tiles under 35% cloud), so
  tiles up to 80% cloud were allowed, with clouds still masked pixel by pixel. Windows 1 to 6 use the first rule.
- The 1 dB rule finds the strongly changed core of the burn, not all of it. It is not tuned or cross-validated.
- In window 2 the placebo test fails on some pairs: before the fires, cells that later burned were already
  losing HV (AUC up to 0.77), and the burned sample is small. Window 1 is the clean case.
- Most radar scenes are provisional releases. Scores use no speckle filter beyond averaging to 200 m.
- Track 155 over Ketapang comes at 20 m pixels, not 10 m; its rule false alarms are much higher (34%).
- Over Merauke, 5 of the 11 track 132 passes carry no HV channel and are left out. The 28 Oct track 61 pass over
  windows 1 to 4 is from the validated (non-provisional) collection.
- Radar change is not fire by itself: water level, rain and land clearing change the echo too.
- The camera did see the ground: on most passes in August and early September, and once per window at the peak
  of the fires. The optical images on the page are surface reflectance, already corrected for the atmosphere,
  so thin haze looks clearer than it was.

## Rebuild it

Needs [uv](https://docs.astral.sh/uv/), a free NASA Earthdata login token and a free FIRMS map key.

```
cp .env.example .env            # then paste your EDL_TOKEN and FIRMS_MAP_KEY into .env
uv sync
uv run python pipeline/search.py                 # list the NISAR GCOV scenes over all eight windows (no login)
uv run python pipeline/stream.py --track 125     # stream the windows out of each scene, about 2 min per window
                                                 # repeat for tracks 61, 155, 90, 10, 119, 112, 47, 124 and 132
uv run python pipeline/firms_pull.py             # VIIRS and MODIS hotspots around windows 1 and 2
uv run python pipeline/firms_pull.py 112.6,-3.2,115.0,-2.2 hotspots_extra.csv    # around windows 3 and 4
                                                 # one more pull per later window, see the note below
uv run python pipeline/merge_firms.py            # join the pulls into data/firms/hotspots.csv
uv run python pipeline/hls_dnbr.py w1            # optical burn map, about 5 min per window
uv run python pipeline/hls_rgb.py w1             # the camera image nearest each radar pass
uv run python pipeline/hls_passes.py w1          # every optical pass of the season, with its cloud share
                                                 # repeat the three hls scripts for w2 to w8
uv run python pipeline/build_site.py             # images, 200 m cells, labels, overlays, meta.json
uv run python pipeline/score.py                  # docs/data/scores.json and the results table above, about 5 min
uv run python tests/test_score.py                # the pipeline's scoring on inputs worked out by hand
node tests/test_score.cjs                        # the page's scoring on the same inputs
node tests/check_scores.cjs                      # the page's scoring equals the pipeline's on the real data
python -m http.server 8765 --directory docs      # open http://127.0.0.1:8765/
```

The FIRMS boxes used for windows 5 to 8 were not written down. Any box that contains a window gives that
window the same hotspots: `firms_pull.py west,south,east,north hotspots_<name>.csv`, then `merge_firms.py`.

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
