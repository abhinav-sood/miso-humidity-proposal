# Project Plan: MISO Load, Humidity, and the 2025-2026 Jump

Working with Dr. Tracey Holloway (UW-Madison). Exploratory paper. A null or messy result is acceptable; a clean, documented, reproducible pipeline is not optional.

## The two questions

- **Question A (original):** Does adding humidity (dew point, later Heat Index) improve prediction of peak summer electricity demand in MISO compared with dry-bulb temperature alone?
- **Question B (new, from Dr. Holloway):** What accounts for the jump in MISO load from summer 2025 to summer 2026? Hypotheses: data centers, more air conditioning, something else (including a change in what MISO reports).

Both use the same pipeline. Build it once.

## Status

- [x] Python environment, folders, LOG.md, `.env` key handling
- [x] Pulled 5-minute `miso_load` for summers 2025 and 2026, saved to `data/raw/`
- [ ] Stage 1 onward (below)

Known facts so far (copy into LOG.md if not already there):
- `miso_load` is 5-minute data. Columns: `interval_start_utc`, `interval_end_utc`, `load`. All UTC.
- Bare start/end strings were read as UTC.
- Rows: 2025 = 27,017, 2026 = 27,820. A full 97 days is 27,936, so 2025 is missing 919 and 2026 is missing 116. The gaps are in the source data.
- Load looks about 20-30% higher in 2026 than 2025 (spot check only, not yet verified).
- Grid Status free plan: 500,000 rows/month. About 242,000 used after the re-pull (period ends Nov 1). Earlier summers cost about 27,000 rows each.
- Metadata says data goes back to Dec 2022.

## Rules (do not break these)

1. **Never edit raw data.** Scripts read `data/raw/` and write `data/processed/`.
2. **Never re-run the pull script** for summers already saved. Every pull costs rows.
3. **Log every problem and decision in LOG.md when it happens, including the reason.**
4. **Choose nothing by looking at test-summer results.** No picking weather points, features, or model forms based on how they do on the test summer.
5. **Scripts must run top to bottom**, with no notebook state.
6. **Check time zones before merging anything.** Join on UTC, convert to local days afterward.
7. Check the Grid Status row cost before any new pull.

## Stage 1: Inspect the saved load files (free)

Script: `01_inspect_load.py`

- [ ] Load each CSV, parse both timestamp columns as UTC datetimes, confirm dtypes
- [ ] Count rows vs. 27,936
- [ ] Measure spacing between consecutive start times; list every gap (start, length)
- [ ] Check duplicate timestamps
- [ ] Check load values: min, max, zeros, spikes
- [ ] Confirm units (expected MW) from the dataset description
- [ ] Log everything in LOG.md

**Done when:** you can state exactly where and how long the gaps are, and that timestamps parse correctly.

## Stage 2: Make the load comparable (free)

Script: `02_prepare_load.py`

- [ ] Aggregate 5-minute load to hourly; log the rule (default: mean of the 12 values)
- [ ] Decide how hours with missing intervals are handled; log it
- [ ] Convert UTC to US Central; log that choice
- [ ] Trim to June 1 - Aug 31 local; flag daylight saving effects
- [ ] Compute daily peak MW, hour of peak, daily total MWh
- [ ] Save to `data/processed/`

**Done when:** one clean table per summer with a row per local day.

## Stage 3: Is the 2025-2026 jump real? (free)

Script: `03_compare_summers.py`

- [ ] Plot daily mean and daily peak for both summers on one chart
- [ ] Compare by hour of day, weekday vs. weekend
- [ ] Check whether MISO changed its footprint or reporting (this would be an artifact, not demand)
- [ ] Log findings

**Done when:** you can say whether the jump is real, and roughly how big.

## Stage 4: Weather data (does not use Grid Status rows)

Script: `04_pull_power.py`

- [ ] Choose 5-10 points across the MISO footprint, weighted toward population centers (Chicago, Minneapolis, Detroit, Indianapolis, St. Louis, New Orleans, Little Rock, etc.). Log the lat/lon.
- [ ] Read NASA POWER docs: hourly endpoint, current parameter names, units, request limits, and the UTC vs. local solar time option. Log it.
- [ ] Pull T2M, T2MDEW, RH2M for both summers (padded dates, UTC)
- [ ] Save raw pulls to `data/raw/` before any processing

**Done when:** raw weather files saved for every point and both summers.

## Stage 5: Merge and sanity check

Script: `05_merge.py`

- [ ] Join load and weather on UTC time
- [ ] Average weather points into one MISO-wide series (simple mean for now)
- [ ] Convert to local days; compute daily Tmax and mean dew point
- [ ] Plot daily peak vs. Tmax

**Done when:** you see load rising with temperature in a curve. If not, **stop and debug before modeling.**

## Stage 6: Answer Question B

Script: `06_jump_analysis.py`

- [ ] Compare the load-vs-temperature curve across summers
  - Vertical shift suggests a roughly constant new load (data centers)
  - Steeper slope suggests more air conditioning
- [ ] Compare mild vs. hot days, afternoon vs. overnight
- [ ] Optional: zone-level MISO load (find the dataset in the catalog; check columns and row cost first)
- [ ] Optional: earlier summers to tell a step from a trend (about 27,000 rows each)

Your data can show the pattern. It cannot prove the cause. Say so.

## Stage 7: Check-in with Dr. Holloway (Phase 5, STOP HERE)

- [ ] Send findings on the jump
- [ ] Decide together, **before any model results exist**:
  - Whether the paper's main question changes
  - How the models handle the year-to-year level shift (for example log load, a year effect, or normalizing each summer)
  - What counts as "meaningfully better" out of sample (about 92 days per summer, so differences are noisy)
- [ ] Wait for her go-ahead

## Stage 8: Models (Question A)

Script: `08_models.py`

- [ ] Add day-of-week and US federal holiday indicators
- [ ] Model 1: peak load ~ Tmax + Tmax^2
- [ ] Model 2: adds mean dew point and Tmax x dew point interaction
- [ ] Train on the earlier summer; test on the later summer
- [ ] Report RMSE, MAPE, R^2, in-sample and out-of-sample
- [ ] Compare predictions, not individual coefficients (Tmax and dew point are correlated)
- [ ] Write 2-3 plain sentences: did humidity help, and by how much?
- [ ] Save the comparison table (CSV) and figures

**Done when:** a comparison table, figures, and a short results summary exist.

## Stage 9: Second pass (only after go-ahead)

- [ ] Model 3: Heat Index (NWS Rothfusz regression with low-temperature/humidity adjustments; record the source for citation) plus its square
- [ ] Population-weighted aggregation (record the population data source)
- [ ] MISO North/Central/South breakdown
- [ ] Hour-of-peak analysis (does the peak shift later on humid days?)
- [ ] Additional summers

## Known risks

- **Level shift:** a model trained on 2025 will miss 2026 by a large constant amount, which can swamp any humidity effect. Handle this deliberately (Stage 7).
- **Small sample:** about 92 days per summer. Don't over-read small differences.
- **Gaps and daylight saving:** missing intervals (especially 2025) and the DST transitions can shift hourly values.
- **Leakage:** never use test-summer data to choose anything.
- **Weather source:** MERRA-2 is gridded reanalysis (0.5 x 0.625 degrees), not station data, and the simple mean over a few points is crude. Both are methods-section limitations.
- **Preliminary data:** recent load data may be revised. Check whether the dataset marks final vs. preliminary.

## Deliverables

- Scripts that rerun end to end, with comments
- LOG.md of problems and decisions
- Figures as files: load vs. temperature, model comparison, predicted vs. observed
- Model comparison table (CSV)
- Short "results so far" summary for the writing chat

## Current step

**Stage 1.** Run `01_inspect_load.py` on both files and log the row counts, dtypes, and gaps.