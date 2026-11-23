# Project Log

## 2026-10-14 | Phase 2 | Grid Status MISO load pull

- **What I did:** Pulled dataset `miso_load` for 2026-05-29 to 2026-09-02 and 2025-05-29 to 2025-09-02. The pull is padded past June 1 and Aug 31 so that edge hours are not lost when I convert time zones and trim later.
- **Dataset facts:** Grid Status describes `miso_load` as load in 5-minute intervals as reported by MISO. Row counts match that: 27,820 rows (2026) and 27,017 (2025). Hourly would have been about 2,300 per summer. Columns: `interval_start_utc`, `interval_end_utc`, `load`. Earliest available data: 2022-12-01 05:00 UTC.
- **Problem 1:** The first run did not save the data to disk, so both pulls were lost when the script ended. Cost: about 54,800 rows. I re-pulled once, with a save step added.
- **Problem 2:** The first pull included `filter_column="load"` with no `filter_value`. The client documentation does not say what this does, so I removed it for the re-pull. Removing it gave identical row counts (27,017 and 27,820), so the filter had no visible effect.
- **Observation:** Both summers have fewer rows than a full 97-day window at 5-minute spacing (27,936). 2026 is short by 116, and 2025 by 919. Details in the 2026-10-19 entry below.
- **Usage:** Free plan, 500,000 rows/month, 250 requests/month, 50,000 rows per response. Before the re-pull: 187,289 rows and 31 requests used this period (period ends Nov 1). The re-pull spent 54,837 rows, leaving 242,126 rows used after it.
- **Time zone answer:** The bare start/end strings (request showed `timezone: None`) were read as UTC. The first row of each year starts at exactly 00:00 UTC on May 29.
- **Open question:** Does resampling in the API reduce rows billed? Not yet verified.
- **Affects:** data/raw/ files, the hourly aggregation step, and the daily peak calculation in Stage 2.

## 2026-10-14 | Phase 2 | Script: initial-run.py (Grid Status pull)

- **Purpose:** Pull 5-minute MISO load from Grid Status and save the raw results to disk.
- **Inputs:** API key from `GRID_STATUS_API_KEY` in `.env` (loaded with python-dotenv). The script stops with a message if the key is missing. Dataset: `miso_load`.
- **Parameters:**
  - Summer 2025: start 2025-05-29 00:00, end 2025-09-03 00:00
  - Summer 2026: start 2026-05-29 00:00, end 2026-09-03 00:00
  - No filters, no resampling (full 5-minute data kept)
- **Outputs:** `data/raw/miso_load_2025_raw.csv` and `data/raw/miso_load_2026_raw.csv` (CSV, `index=False`).
- **Safeguards:** Each dataframe is saved immediately after its pull. The pull is skipped if that year's file already exists, so re-running costs no API rows. Usage is printed before and after.
- **Changes from first version:** Removed `filter_column="load"` and added the save step (the first version lost its data).
- **Rule:** Do not re-run this script for these summers. Raw files are never edited.

## 2026-10-19 | Phase 2 | Script: 01_inspect_load.py (inspect saved load files)

- **Purpose:** Read the two raw CSVs and check them. Reads only; writes nothing.

### Loading
- Loaded both files with `parse_dates` on both timestamp columns. Both time columns are `datetime64[ns, UTC]` and `load` is `int64`. Row counts: 27,017 (2025) and 27,820 (2026), matching the saved files. First rows match the pull output (2025 starts at 75,379; 2026 at 93,012).

### Gaps
- **Method:** Took the difference between consecutive `interval_start_utc` values and counted each distinct spacing.
- **2025:** 26,896 normal 5-minute intervals. 119 short gaps (89 of one missing reading, 30 of two to six missing), totaling 184 missing readings. One large gap of 2 days 13 h 20 min, about 735 missing readings. 184 + 735 = 919, the full shortfall. No spacing shorter than 5 minutes, so no duplicate timestamps.
- **2026:** 27,750 normal intervals. Only short gaps, the longest 1 h 15 min (14 missing readings, on 2026-08-16 from 16:00 to 17:15 UTC, which is 11:00 a.m. to 12:15 p.m. Central). Total missing: 116, the full shortfall. No duplicates.
- **2025 large gap:** Data stops after the interval ending 2025-05-30 15:45 UTC and resumes at 2025-06-02 05:00 UTC (CDT: Fri May 30 10:45 a.m. to Mon June 2 12:00 a.m.). **Local June 1, 2025 (a Sunday) has no data at all**, so the 2025 summer has 91 usable days. May 30-31 fall in the padding and do not matter.
- **Decision:** Exclude local June 1, 2025 from daily peaks and models. Do not interpolate a whole missing day, because it would create invented data that models would treat as real.
- **Cause of gaps:** Unknown. They are in the source data, not caused by my query.

### Load values
- **Range:** 2025 min 58,917 and max 121,139. 2026 min 62,210 and max 124,244. Zero readings: 0 in both years.
- **Year-to-year difference:** 2026 max is about 2.6% higher and 2026 min about 5.6% higher than 2025. **Correction:** an earlier spot check of the first and last rows suggested a 20-30% difference. That was a comparison of single early-summer and late-summer readings, which weather can explain, and it overstated the difference. A proper comparison of daily mean and peak is pending (PLAN.md Stage 3). Do not quote a jump size until that is done.
- **Units:** Grid Status describes grid load as measured in megawatts (MW) (source: Grid Status website, per my reading of the site). The values are consistent with MW at the MISO system scale.

### Largest changes between consecutive readings
- **Raw absolute changes:** 11,077 MW (2025) and 5,481 MW (2026). Both sit exactly at data gaps, not between readings 5 minutes apart. 2025: row 469, the 2.6-day gap (75,114 before, 64,037 after, Friday morning to Sunday night Central). 2026: row 22860, the 1 h 15 min gap on 2026-08-16 (92,874 before, 98,355 after, during the normal morning ramp). Not data errors.
- **Changes restricted to readings exactly 5 minutes apart:** 26,896 changes (2025) and 27,750 (2026), matching the counts of normal intervals.
  - 2025: median 229 MW, 99th percentile 718 MW, max 2,190 MW
  - 2026: median 232 MW, 99th percentile 726 MW, max 2,083 MW
  - The two summers behave almost identically.
- **The two largest 5-minute changes, inspected:**
  - 2025-07-10 15:20 UTC (10:20 a.m. Central): load was climbing (93,178, 93,470, 93,864), dipped for two readings (92,952, 92,965), then returned to trend (95,155). Looks like a brief reporting dip of about 1,300-1,700 MW.
  - 2026-06-02 04:40 UTC (11:40 p.m. Central on June 1): load was falling (77,339 to 76,256), one reading of 74,173, then 75,132 and the decline resumed. A one-reading dip of about 1,500 MW.
- **Decision:** Leave raw data unchanged. Both dips are about 2% of system load, are dips rather than upward spikes, and are far from daily peaks. Averaging to hourly shrinks a one-reading dip of this size to about 125 MW. Cause unknown; not corrected.
- **Not yet done (optional):** count of real 5-minute changes above 1,000 MW in each year, to confirm they are rare.

### Software note
- pandas raised a DeprecationWarning ("generic unit for NumPy timedelta") when comparing `time_diff` to `pd.Timedelta(minutes=5)`. Results matched expected counts, so I treated them as correct. [Add pandas and numpy versions from requirements.txt.]

### Stage 1 status
- Complete. Raw load files load correctly, gaps are characterized, no duplicates, no zeros, units confirmed, no spike problems.
- Stage 2 rules were decided on 2026-10-20 (see next entry).

## 2026-10-20 | Phase 2 | Stage 2 rules for hourly aggregation (decided before any hourly results)

- **Rule 1, hour assignment:** Each 5-minute reading belongs to the hour of its `interval_start_utc`, rounded down. Reason: using the start time keeps each reading in the hour it mostly covers, and the weather data must use the same hour convention so load and weather line up.
- **Rule 2, aggregation:** Hourly load is the mean of the readings present in that hour (not the sum divided by 12). Daily peak is the highest hourly mean, not the highest single 5-minute reading. Reason: hourly averages are the standard unit for comparison, and the paper must state that "daily peak" means highest hourly average, which is a little lower than the highest instantaneous reading.
- **Rule 3, minimum coverage:** An hour is kept only if it has 9 or more of 12 readings (at least 45 minutes of coverage). Hours with 8 or fewer are marked missing and not filled in. Reason: tolerates the common 1-2 reading gaps but avoids false lows or highs from hours built on a few readings.
- **Known example:** On 2026-08-16, the gap leaves the 11:00 a.m. Central hour (16:00 UTC) with 1 reading, so it is dropped. The next hour (17:00 UTC) has 9 readings but is missing its first 15 minutes, which are in a ramp, so its mean runs slightly high. Minor; noted here.
- **Open rule, days with a dropped hour:** A day with a missing hour has an incomplete daily MWh, and its peak could be understated if the missing hour is near the afternoon peak. Decide after counting how many days are affected. Do not decide based on how those days affect model results.
- **To do in Stage 2:** (1) After aggregating, count dropped hours in each year and list their dates. (2) Count days with at least one dropped hour. (3) Set and log the day rule. (4) Log the final number of usable days (expected 91 for 2025 and 92 for 2026, minus any excluded under the day rule).
- **Affects:** 02_prepare_load.py, daily peak, hour of peak, daily MWh, and the number of usable days.

## 2026-10-27 to 2026-11-22 | Weather pull, merge, and what changed (written up 2026-11-23, partly from memory of the work; check dates)

- **NASA POWER weather pull (first version).** Hourly point API, `time-standard: utc`, `-999` = missing, 8 points averaged equally (Minneapolis, Madison, Detroit, St. Louis, Des Moines, Indianapolis, New Orleans, Little Rock). Variables first: T2M, T2MDEW, RH2M. 16 files saved to `data/raw/nasa_power/`. Inspection (05b): all 16 files complete.
- **Madison replaces Milwaukee.** Decision: use Madison. Milwaukee files moved to `data/raw/nasa_power_unused/` (not deleted). [Owed: write the reason in one sentence.]
- **06_merge.py.** Joined load and weather on UTC, then converted to Central days. Bug found: `load_2025` was reading the 2026 file. The shape check could not catch it. Fixed by reading each year's own file and adding `assert load.index.is_unique`. Also fixed typos (`repalce`, wrong column names, a `.is_file()` call on a string).
- **Dew point problem.** MERRA-2 dew point was sometimes above air temperature (example 11.75 vs 11.49 C). I first called it minor; that was wrong. Dr. Holloway said MERRA-2 dew point is unreliable. Decision: do not use dew point. Use specific humidity `QV2M` instead. [Owed: count of hours with dew point above T2M. RH2M may have the same problem; not used.]
- **Second weather pull (v2).** Re-pulled with new variables: T2M, QV2M, solar (ALLSKY_SFC_SW_DWN), wind, rain. 16 files in `data/raw/nasa_power_v2/`. Old pull kept. [Owed: confirm units of QV2M and solar; solar max ~3.5 is probably MJ/m2/h but not confirmed.]
- **Missing solar hours.** 2026-09-01 00:00 to 2026-09-02 23:00 UTC is missing (48 hours, found with 05e). It affects 2026-08-31 local (last 5 hours). Decision: exclude 2026-08-31 from every model. Reason: dropping one day for all models is simpler than filling invented sunlight values.
- **Dr. Holloway's guidance:** avoid MERRA-2 dew point; use straight machine learning as a proof of concept; regression stays as the simple baseline. Main question (approved): how close can an open model on NASA POWER weather get to MISO's own day-ahead forecast, and does humidity help beyond temperature? Secondary: the 2025 to 2026 difference (about +2.5%, not the 20-30% from the early spot check).
- **Correlations / year comparison (06b).** Peak load rises with tmax in both summers; 2026 is about 1.2 C warmer and peaks are about 2.5% higher.
- **Weather timing question.** NASA POWER is observed weather, not a forecast, and arrives 2-3 days late. For a historical study the delay does not matter (earlier claim that it blocks the study was overstated and is withdrawn). It matters only for live use. Decision: report two designs: same-day weather (best case) and day-before weather (forecast-style).

## 2026-11-2x | Grid Status forecast pull

- **Dataset:** `miso_load_forecast_mid_term_by_region`. About 7 versions per hour (one published per day at 05:00 UTC), 10 zones Z1-Z10.
- **Pull:** one request per summer, 156,240 rows each. Usage after: 314,709 rows of 500,000, 10 requests. Files: `data/raw/miso_forecast_mid_term_{2025,2026}_raw.csv`. A test pull (`miso_forecast_test_20250601.csv`) is also kept. The test script had `filter_column="load"`, which does not exist in this dataset; removed.
- **Inspection (07b):** clean. The latest version of each hour is published 24-47 hours before the hour.
- **Day-ahead rule:** use the latest version of each hour. Sum the 10 zones. Convert to Central. Forecast daily peak = highest hour of the Central day (same definition as actual peak). Script: `08_forecast_daily.py`.
- **Caveat:** this is the mid-term product, not necessarily MISO's own day-ahead forecast. Publish times look like date stamps.

## 2026-11-23 | Model design, fixed before any 2026 results (scripts 09-11)

- **Rule:** Nothing was chosen by looking at 2026 results. Pipeline was written and tested on synthetic data only.
- **Days used:** same days for every model. Left out: first 2 days of each summer (no lagged weather), days not usable because of missing load (2025-06-01 has no load data; others per 06_merge), and 2026-08-31 (solar). 90 train (2025) and 89 test (2026) days. Left out: 2025-06-01/02, 2026-06-01/02, 2026-08-31.
- **Features:** tmax, mean specific humidity (qv_mean), mean sunlight, mean wind, total rain; tmax of the day before the weather day; heat streak (consecutive days with tmax above the 75th percentile of 2025 tmax, 2025 only so no test data is used). Calendar: day of week (Monday baseline) and holiday flag (2025-06-19, 2025-07-04, 2026-06-19, 2026-07-03, 2026-07-04; July 4, 2026 is a Saturday so Friday July 3 is also flagged).
- **Models:** Regression R1 = tmax + tmax^2 + calendar; R2 = R1 + qv_mean + tmax x qv_mean. Machine learning: gradient boosting (primary) and random forest, with nested inputs E1 temperature, E2 + humidity, E3 + sun/wind/rain, E4 + previous-day temperature and heat streak. All ML models get the calendar features.
- **Tuning:** 5-fold contiguous-block cross-validation inside 2025 only. Grids: RF max_depth {3,5,None} x min_samples_leaf {2,5}; GBM n_estimators {100,300} x max_depth {2,3}; fixed seed 42.
- **Tests:** fixed split (train 2025, test 2026) and walk-forward (each 2026 day predicted from all days at least 2 days older). Code asserts the training set never includes the target day or later days.
- **Metrics:** RMSE, MAE, MAPE, R-squared, bias (prediction minus actual). Differences judged with a 7-day moving-block bootstrap (2,000 resamples), 95% interval. "Meaningfully better" = interval excludes zero. [Needs Dr. Holloway's OK.]
- **Checks done on synthetic data:** metrics recomputed by hand match the script (14 checks); lag alignment checked row by row; shuffling 2026 outcomes does not change predictions or chosen settings (no leakage); with no planted humidity effect nothing is flagged, with a strong one the same-day models flag it. Day-before models could not detect it on synthetic data because yesterday's synthetic weather barely predicts today's load.
- **Known limits:** tree models cannot extrapolate above the hottest 2025 days; ~90 test days; simple 8-city mean; no population weighting.

## 2026-11-23 | First real run of scripts 08-11 (all numbers are on the 89 test days of summer 2026)

- **Run:** 08 and 09 ran clean (lead time 24-47 h; 90 train / 89 test days). 10 took 245 s. 11 produced the report and four figures.
- **Reframing decided today:** the headline is the DAY-BEFORE weather (a real forecast setting: only information available a day ahead). SAME-DAY weather is shown only as an upper bound. Reason: a forecast never sees the target day's weather; NASA POWER only gives observed weather, so no true weather forecast is available (data source kept to NASA POWER only). 11_report.py was changed to lead with day-before.
- **MISO day-ahead forecast:** RMSE 2.18 GW (MAPE 1.62%, bias +0.86 GW).
- **Day-before (forecast setting):** regression temperature only 4.72 GW; regression + humidity 4.54 GW; gradient boosting + humidity 5.16 GW; other ML models 5.1 to 5.8 GW. All clearly worse than MISO (differences +2.4 to +3.3 GW, intervals exclude zero). Likely cause: yesterday's weather instead of a weather forecast.
- **Humidity in the forecast setting:** no clear difference. Regression -0.18 GW (95% interval -0.80 to +0.48); gradient boosting +0.09 GW (-0.43 to +0.76); random forest +0.24 GW (-0.27 to +0.93). Same result in walk-forward.
- **Upper bound (same-day weather):** regression + humidity 2.45 GW (not distinguishable from MISO); gradient boosting + humidity 3.75 GW. Humidity helped the regression here: 3.91 to 2.45 GW (interval -2.09 to -0.52); walk-forward -0.68 GW (-1.04 to -0.13). Part of this may be humidity absorbing the 2025-to-2026 level shift: bias of the regression fell from +2.47 to +0.21 GW when humidity was added. Two clear wins out of 12 humidity comparisons, so treat as a lead only.
- **Machine learning did not beat the simple regression** in either setting (about 90 training days).
- **Check done:** random forest test RMSE was nearly identical across input sets (4.52-4.54 GW, same-day). best_params.csv and model_comparison.csv show the models and settings differ (training RMSE 3.2-3.4 GW), so this is a plateau from trees not predicting above the 2025 range, not a bug.
- **Open for Dr. Holloway:** headline = day-before OK? level shift handling; what counts as meaningfully better; next variables or weighting.

## Still owed to this log
- MISO fills per year and number of partial hours replaced (from 06/02 steps).
- Package versions (pandas, numpy, scikit-learn, matplotlib, xlrd, gridstatusio).
- Dew point > T2M hour count; units of QV2M and solar.