# Project Plan: MISO load, NASA POWER weather, and MISO's own forecast

Working with Dr. Tracey Holloway (UW-Madison). Exploratory paper. A clean, documented, reproducible pipeline matters more than a positive result. Updated 2026-11-23.

## The questions
- **Main (approved):** How close can an open model built on NASA POWER weather get to MISO's own day-ahead load forecast, and does humidity help beyond temperature alone?
- **Secondary:** What explains the 2025 to 2026 load difference (about +2.5%; 2026 was also about 1.2 C warmer)? Data can show the pattern, not prove a cause.

## Rules (do not break)
1. Never edit raw data. 2. Never re-run the load pull. 3. Log every decision with the reason. 4. Choose nothing by looking at test-summer (2026) results. 5. Scripts run top to bottom. 6. Join on UTC, then convert to Central days. 7. Check Grid Status row cost before any pull (314,709 of 500,000 used this month). 8. Keep filled hours labelled by source. 9. API key only in `.env`.

## Status
- [x] Stage 1 inspect load. [x] Stage 2 hourly/daily load. [x] Stage 4 weather pulls (v2 variables: T2M, QV2M, sun, wind, rain). [x] Stage 5 merge and sanity plot (peak rises with temperature).
- [x] Forecast pull (`07`), inspection (`07b`), daily forecast (`08`).
- [x] Model pipeline written and tested on synthetic data (`09`, `10`, `11`).
- [ ] **Run `08` to `11` on the real data (next step)** and read `outputs/RESULTS.md`.
- [ ] Stage 3/6 year comparison write-up (secondary question), only lightly done.
- [ ] Meeting with Dr. Holloway on the open decisions below.
- [ ] LOG.md: fill the "still owed" items.

## Pipeline order
`06_merge.py` -> `08_forecast_daily.py` -> `09_build_features.py` -> `10_models.py` (5-10 min; `--skip-walk-forward` for a quick run) -> `11_report.py`. See RUN_NOTES.md.

## Decisions needed from Dr. Holloway
1. Same-day weather (best case) vs day-before weather (forecast-style): which is the headline?
2. Handling of the 2025 to 2026 level shift (walk-forward now; log-load or a year term as an option).
3. What counts as "meaningfully better" (current: 95% block-bootstrap interval excludes zero).
4. Next steps: population-weighted weather, more points, Heat Index, hour-of-peak, more summers.

## Known risks
Observed vs forecast weather; level shift between summers; tree models cannot predict above the training range; only about 90 test days; mid-term forecast product may differ from MISO's true day-ahead; equal-weight 8-city mean; MERRA-2 is gridded reanalysis; days excluded (see LOG.md).

## Deliverables
Scripts (06, 08-11), LOG.md, `outputs/RESULTS.md`, tables and four figures in `outputs/`, and a short write-up for Dr. Holloway built from the real numbers.
