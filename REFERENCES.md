# References

A running list of every dataset, tool and source this project uses. Updated with each change.
AI tools are described in the README under "AI use".

## NASA data

| What | Used for | Source |
|---|---|---|
| NISAR L2 Geocoded Polarimetric Covariance (GCOV), L-band, HH and HV, 10 m. Provisional product, Version 1 (19 scenes) | Radar backscatter before and during the fire season | NASA and ISRO, distributed by the Alaska Satellite Facility DAAC. https://doi.org/10.5067/NIL2GCOV-P1 |
| NISAR L2 GCOV, Validated product, Version 1 (1 scene, 1 Nov 2026) | Same | https://doi.org/10.5067/NIL2GCOV-V1 |
| VIIRS 375 m active fire detections, near real-time (Suomi NPP, NOAA-20, NOAA-21), 22 Jun to 13 Nov 2026 | Hotspot layer | NASA FIRMS, https://firms.modaps.eosdis.nasa.gov/ (area API). We acknowledge the use of data from NASA's Fire Information for Resource Management System (FIRMS), part of NASA's Earth Science Data and Information System (ESDIS) |
| HLS Sentinel-2 MSI Surface Reflectance Daily Global 30 m v2.0 (HLSS30) | Optical burn map | NASA LP DAAC. https://doi.org/10.5067/HLS/HLSS30.002 |
| HLS Landsat OLI Surface Reflectance Daily Global 30 m v2.0 (HLSL30) | Optical burn map | NASA LP DAAC. https://doi.org/10.5067/HLS/HLSL30.002 |

## NASA resources from the challenge's Resources tab

- ASF Data Search (Vertex) and the ASF search API: https://search.asf.alaska.edu/
- NISAR Data User Guide, GCOV page: https://nisar-docs.asf.alaska.edu/gcov/
- NASA Earthdata Search and the Common Metadata Repository (CMR) API: https://search.earthdata.nasa.gov/search
- Intro to Synthetic Aperture Radar: https://www.earthdata.nasa.gov/learn/earth-observation-data-basics/sar

## Method sources

- Streaming NISAR products over HTTPS without a full download: ASF NISAR Cookbook, "Search and Stream NISAR Data with asf_search". https://asfopensarlab.github.io/NISAR_Cookbook/notebooks/search-stream-nisar-asf-search
- dNBR burn severity classes (unburned below 0.10, moderate-low from 0.27, moderate-high from 0.44), proposed by the USGS, as given in UN-SPIDER, "Normalized Burn Ratio (NBR)". https://un-spider.org/advisory-support/recommended-practices/recommended-practice-burn-severity/in-detail/normalized-burn-ratio
- VIIRS 375 m active fire algorithm: Schroeder, W., Oliva, P., Giglio, L., and Csiszar, I. A. (2014). The New VIIRS 375 m active fire detection data product: algorithm description and initial assessment. Remote Sensing of Environment, 143, 85 to 96. https://doi.org/10.1016/j.rse.2013.12.008
- NASA FIRMS FAQ (what a detection is, sensors and latency): https://www.earthdata.nasa.gov/data/tools/firms/faq
- Indonesian Ministry of Forestry press release, 8 Nov 2026 (hotspot counts are not burned area; peat fires in Pulang Pisau still being fought): https://www.kehutanan.go.id/news/hotspot-nasional-naik-jadi-165-titik-kalteng-kembali-jadi-fokus-penanganan

## Software

Python: asf_search, h5py, fsspec, aiohttp, numpy, pandas, scipy, rasterio (GDAL, PROJ), pyproj, Pillow, requests, python-dotenv, managed with uv.
Checks: Node.js for the scoring check, Playwright with Microsoft Edge for page captures.
The page itself is plain HTML, CSS and JavaScript with no libraries and no external requests.

## Challenge

NASA Space Apps Challenge 2026, "Dancing with the SARs": https://www.spaceappschallenge.org/2026/challenges/dancing-with-the-sars/
