# Project Plan: Humidity and an Open NASA-Based Load Model for MISO

Working with Dr. Tracey Holloway (UW-Madison). Exploratory paper. A null or messy result is acceptable; a clean, documented, reproducible pipeline is not optional.

## The questions (focus approved by Dr. Holloway, 2026-10-27)

**Main question (combines A and C):** How close can an open model built on NASA POWER weather get to MISO's own day-ahead load forecast, and does adding humidity (dew point, later Heat Index) improve it compared with temperature alone?

- **A. Humidity:** does adding dew point improve prediction of daily peak load beyond temperature alone?
- **C. Benchmark:** compare my models' errors with MISO's published day-ahead load forecast errors, same metrics, same test summer.
- **B. The 2025-to-2026 difference (secondary):** daily peak is about 2.5% higher in 2026 (unadjusted for weather). Is it weather, growth (data centers, more air conditioning), or something else? Uses the same data. Descriptive only; the data cannot prove a cause.

## Status

- [x] Stage 1: raw load files inspected
- [x] Stage 2: hourly load, MISO gap fill, daily table (scripts 02, 03, 04)
- [ ] Stage 4 onward

Facts so far (details in LOG.md):
- `miso_load` is 5-minute, in UTC. Raw files in `data/raw/` are never edited.
- Gaps (919 missing 5-minute readings in 2025 including all of local June 1, 116 in 2026) were filled from MISO's own report (`_df_al.xls`, market day D is in the file dated D+1). Validation on six days: median difference 0.3%, 95th percentile 0.6%; MISO's hour convention fits at shift 0.
- Both summers have 92 usable Central-time days. "Daily peak" means the highest HOURLY mean.
- Unadjusted 2026 vs. 2025: daily peak +2.5%, daily mean +2.7%, daily minimum +3.8%. (An early spot check suggesting 20-30% was wrong.)
- Grid Status free plan: 500,000 rows/month; about 242,000 used this period. The period resets 2026-11-01.

## Rules (do not break these)

1. **Never edit raw data.** Scripts read `data/raw/` and write `data/processed/`.
2. **Never re-run the load pull script** for summers already saved. Every pull costs rows.
3. **Log every problem and decision in LOG.md when it happens, including the reason.**
4. **Choose nothing by looking at test-summer results.** No picking weather points, features or model forms based on how they do on the test summer.
5. **Scripts must run top to bottom**, with no notebook state.
6. **Check time zones before merging anything.** Join on UTC, convert to Central days afterward.
7. Check the Grid Status row cost before any new pull.
8. Filled hours stay labelled by source (`gridstatus`, `miso_dfal`, `missing`).

## Stage 1-2: Load data (DONE)

Scripts: `01_inspect_load.py`, `02_prepare_load.py`, `03_fill_from_miso.py`, `04_daily_table.py` (plus `03_explore_raw_miso_file.py`, exploration only).

Outputs: `data/processed/hourly_load_utc_*.csv`, `hourly_load_filled_utc_*.csv`, `daily_load_*.csv`, `daily_load_all.csv`; `outputs/tables/` (validation, fill log, summer comparison); two figures.

Still to record in LOG.md: hours filled from MISO per year, partial hours replaced, package versions (including xlrd).

## Stage 4: Weather data (does not use Grid Status rows)

Script: `05_pull_power.py`

- [ ] Confirm the final list of points (proposed: Minneapolis, Milwaukee, Detroit, St. Louis, Des Moines, Indianapolis, New Orleans, Little Rock; Madison undecided). Log lat/lon and the reason. Chicago is PJM, not MISO.
- [ ] Read the OFFICIAL NASA POWER hourly page: endpoint, parameter names (T2M, T2MDEW, RH2M), community and units, missing-value code, date range limit, latest available date. Log it.
- [ ] **Request UTC explicitly.** The default time standard is LST (local solar time).
- [ ] Pull both summers, padded dates (May 29 to Sep 2, as for load). Save raw pulls first, one file per point and year.
- [ ] Check: daily temperature peaks at about 20-22 UTC in summer. If it peaks near hour 14-16, it is not UTC.
- [ ] Check for missing values and gaps in each point.

**Done when:** raw weather files saved for every point and both summers, and the time check passes.

## Stage 5: Merge and sanity check

Script: `06_merge.py`

- [ ] Join hourly filled load (UTC) and weather (UTC) on the UTC hour
- [ ] Average weather points into one MISO-wide series (simple mean)
- [ ] Convert to Central days; compute daily Tmax and mean dew point
- [ ] Plot daily peak vs. Tmax

**Done when:** load rises with temperature in a curve. If not, **stop and debug before modeling.**

## Stage 6: The 2025-2026 difference (secondary question B)

Script: `07_jump_analysis.py`

- [ ] Compare the load-vs-temperature curve across summers. A vertical shift suggests a roughly constant added load; a steeper slope suggests more cooling load.
- [ ] Mild vs. hot days; afternoon vs. overnight; weekday vs. weekend
- [ ] Optional: MISO zone-level load (check dataset columns and row cost first); earlier summers to tell a step from a trend
- Report as a pattern, not a cause.

## Stage 7: Check-in with Dr. Holloway (STOP HERE before models)

- [x] Focus approved (2026-10-27)
- [ ] Her answer: predict load from OBSERVED weather, or forecast ahead? (Observed means the benchmark favors my models; say so in the paper.)
- [ ] Decide before any model results exist:
  - How the models handle the 2025-to-2026 level shift (about 2.5 GW; for example log load, a year effect, or normalizing each summer)
  - What counts as "meaningfully better" out of sample (about 92 days per summer, so differences are noisy)

## Stage 8: Models (question A)

Script: `08_models.py`

- [ ] Day-of-week and US federal holiday indicators
- [ ] Model 1: peak load ~ Tmax + Tmax^2
- [ ] Model 2: adds mean dew point and Tmax x dew point
- [ ] Train on the earlier summer; test on the later summer
- [ ] RMSE, MAPE, R^2, in-sample and out-of-sample
- [ ] Compare predictions, not individual coefficients (Tmax and dew point are correlated)
- [ ] 2-3 plain sentences: did humidity help, and by how much?
- [ ] Save the comparison table (CSV) and figures

## Stage 8b: Benchmark against MISO's forecast (question C)

Script: `09_benchmark.py`. Start after 2026-11-01 (row quota reset).

- [ ] Find MISO load forecast datasets in the Grid Status catalog; read metadata (resolution, date range, columns); estimate row cost BEFORE pulling
- [ ] Pull the day-ahead load forecast for both summers; save raw
- [ ] Turn it into daily peak forecasts the same way as actual load (highest hourly value, Central day)
- [ ] Compute RMSE, MAPE and R^2 for MISO's forecast on the same days as my test summer
- [ ] Compare with Models 1 and 2. Caveat: my models use observed weather; MISO's forecast must predict it.
- [ ] Verify at the source whether MISO's forecasts use dew point before saying so in the paper

## Stage 9: Second pass (only after go-ahead)

- [ ] Model 3: Heat Index (NWS Rothfusz regression with low-temperature/humidity adjustments; record the source) plus its square
- [ ] Population-weighted aggregation (record the population data source)
- [ ] MISO North/Central/South breakdown
- [ ] Hour-of-peak analysis (does the peak shift later on humid days?)
- [ ] Additional summers

## Known risks

- **Observed vs. forecast weather:** POWER describes weather that already happened. Models predict load given the weather; MISO's forecast also predicts the weather. State this.
- **Level shift:** about 2.5 GW between summers. Smaller than first feared, but comparable to the effect being tested. Decide handling before fitting.
- **Small sample:** about 92 days per summer.
- **Time zones:** the POWER default is LST, not UTC. Request UTC and check.
- **Filled hours:** from a different source (MISO submitted meter data). Report the validation and the count.
- **Leakage:** never use test-summer data to choose anything.
- **Weather source:** MERRA-2 is gridded reanalysis (0.5 x 0.625 degrees), not station data, and a simple mean over 8 points is crude.
- **Preliminary data:** recent load data may be revised.

## Deliverables

- Scripts that rerun end to end, with comments
- LOG.md of problems and decisions
- Figures as files: load vs. temperature, model comparison, predicted vs. observed
- Model comparison table (CSV), including the MISO forecast benchmark
- Short "results so far" summary for the writing chat

## Current step

**Stage 4.** Confirm the weather points (and the Madison decision), then read the official NASA POWER hourly page and log what it says.