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
- **Decision:** Exclude local June 1, 2025 from daily peaks and models. Do not interpolate a whole missing day, because it would create invented data that models would treat as real. **SUPERSEDED 2026-10-22:** Dr. Holloway asked me to fill gaps from MISO's own reports. MISO has real values for this day, so June 1, 2025 is filled from MISO instead of excluded, subject to the validation in the 2026-10-22 entry. Still no interpolation.
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

## 2026-10-22 | Phase 2 | Filling gaps from MISO reports (Dr. Holloway's instruction)

- **Instruction:** Dr. Holloway said to fill the missing data directly from the MISO reports. This replaces my earlier plan to exclude June 1, 2025.
- **Source report:** MISO "Forecasted and Actual Load Report" (Historical Daily Forecast and Actual Load by Local Resource Zone), files named `{YYYYMMDD}_df_al.xls` at docs.misoenergy.org/marketreports/. Inspected two files with `03_explore_raw_miso_file.py` (dates 20250715 and 20250601).
- **Facts found in the files:**
  - Real binary Excel (.xls) files, not HTML tables. Read with `pd.read_excel(header=4)`; needs the `xlrd` package.
  - Each file covers 7 days starting the day before its date, but holds ACTUAL load only for the first day; the other six days are forecast only. **Market day D comes from the file dated D+1.** (Observed: file 20250715 has actuals for July 14; file 20250602 has actuals for June 1.)
  - Hourly data (not 5-minute), columns per zone plus `MISO ActualLoad (MWh)`. The six zone columns add up to the MISO total (checked on the first row of 20250715: 75,233.06).
  - `HourEnding` runs 1-24 (hour ending 1 = the first hour of the market day). Units are MWh per hour, i.e. average MW.
  - The file says "submitted meter data", so it may differ slightly from the real-time series behind Grid Status `miso_load`.
  - MISO has data for June 1, 2025, a day completely missing from Grid Status, so that hole is in the Grid Status data (not necessarily in MISO's).
- **Time convention (UNVERIFIED in the file itself):** MISO's clock is believed to be fixed EST (UTC-5) all year; in summer that equals Central daylight time. The script tests this against Grid Status before filling, instead of assuming it.
- **Pipeline now:** `02_prepare_load.py` (hourly UTC tables, saved to data/processed) -> `03_fill_from_miso.py` (validate, then fill) -> `04_daily_table.py` (Central-time daily table, comparison tables and figures).
- **Validation rules (set BEFORE looking at the comparison):**
  - Test days: the 15th of June, July and August in each year (6 days; a fixed rule, not hand-picked).
  - Compare MISO hourly values with Grid Status hourly means. Test hour shifts of -3 to +3 hours; the documented convention (shift 0) must fit best.
  - At shift 0: median absolute difference at most 1.0%, 95th percentile at most 3.0%, at least 72 overlapping hours.
  - If any check fails, nothing is filled and the script stops. [Confirm or change these thresholds BEFORE the first run, and note it here.]
- **Fill rules:**
  - Only hours that are empty in the Grid Status hourly table are filled, and only inside the June 1 - Aug 31 Central window. Existing Grid Status values are never overwritten.
  - This includes hours dropped by the 9-of-12 rule (1-8 readings): the MISO value replaces the partial Grid Status hour.
  - No interpolation. Each filled hour is listed in `outputs/tables/miso_fill_log.csv`, and every hour is labelled in the `source` column (`gridstatus`, `miso_dfal`, or `missing`).
- **Day rule (settled; was the open rule above):** A local day is "usable" only if all 24 hours are present after filling. Other days stay in the daily table but are flagged `usable = False`. Reason: a missing hour could hide the day's true peak. Decided from the data structure, before any model results exist. [Record the number of flagged days.]
- **Testing note:** Scripts 02-04 were tested end to end on SYNTHETIC data shaped like the real files, including a wrong-hour-shift case (validation correctly stopped the fill) and a missing-report case (affected days correctly flagged). The real MISO download step could not be tested here, so the first real run is the real test.
- **Methods-section caution:** filled hours come from a different source (MISO submitted meter data, hourly) than the rest (Grid Status 5-minute real-time load, averaged to hourly). Report the validation result and the count of filled hours.
- **Affects:** all daily peaks, hour of peak and daily MWh, the number of usable days in 2025 (now 92, not 91), and the Stage 3 comparison.

## 2026-10-23 | Phase 2 | First real run of 02, 03 and 04: results

- **All three scripts ran to completion** on the real data, with no errors.
- **MISO validation passed.** Six validation days (the 15th of June, July and August in each year), 143 overlapping hours (144 possible; one hour had no Grid Status value to compare). Percent difference = (MISO - Grid Status) / Grid Status.

  | Hour shift | Median abs % | 95th pct abs % | Max abs % | Mean signed % |
  |---|---|---|---|---|
  | -1 | 3.346 | 6.531 | 7.170 | 0.169 |
  | **0** | **0.303** | **0.604** | **0.768** | **0.029** |
  | +1 | 2.713 | 5.649 | 6.456 | 0.020 |

  (Shifts of +/-2 and +/-3 hours are worse still; full table in `outputs/tables/miso_validation_summary.csv`.)
- **What this means:**
  - The documented hour convention fits best by a wide margin. Shift 0 is about 9 times better than shift +1 or -1 on the median, so the MISO hours line up with the Grid Status hours as assumed (MISO clock = UTC-5 all year = Central daylight time in summer).
  - Thresholds met (set before the run): median 0.303% vs. a limit of 1.0%, 95th percentile 0.604% vs. a limit of 3.0%.
  - No systematic offset: the mean signed difference is +0.029%, so MISO's submitted meter data and the Grid Status real-time series agree on average. No bias correction was applied or needed.
- **Fill result:** both years have 92 days, all usable (all 24 hours present), so no days were flagged unusable. Evidence: the unadjusted comparison used usable days only and counts 92 days in each year (2025: 65 weekdays + 27 weekend days; 2026: 66 weekdays + 26 weekend days; these match the calendar). Local June 1, 2025 is therefore filled from MISO and included.
- **Still to fill in from the `03` printout or `outputs/tables/miso_fill_log.csv`:**
  - Number of hours filled from MISO: 2025 ___, 2026 ___.
  - Hours that had partial Grid Status data (1-8 readings) and were replaced by MISO values (column `replaced_partial_gridstatus_hour`): ___.
  - `xlrd` version (needed to read .xls), and pandas and numpy versions, in the software note.

### Unadjusted comparison of the two summers (NOT controlled for weather)

Source: `outputs/tables/summer_comparison.csv`; 92 usable days per year. Peak = highest hourly mean in a Central-time day.

| Days | Measure | 2025 mean (MW) | 2026 mean (MW) | Difference |
|---|---|---|---|---|
| all | daily peak | 102,923 | 105,441 | +2.45% |
| all | daily mean | 87,316 | 89,683 | +2.71% |
| all | daily minimum | 70,128 | 72,763 | +3.76% |
| weekdays | daily peak | 104,672 | 107,206 | +2.42% |
| weekdays | daily mean | 88,963 | 91,374 | +2.71% |
| weekdays | daily minimum | 71,093 | 73,796 | +3.80% |
| weekends | daily peak | 98,711 | 100,961 | +2.28% |
| weekends | daily mean | 83,351 | 85,389 | +2.44% |
| weekends | daily minimum | 67,803 | 70,141 | +3.45% |

- **Size of the 2025 to 2026 difference:** about +2.5% on daily peak (roughly 2.5 GW) and +2.7% on daily mean, about +3.8% on the daily minimum. **This settles the earlier correction: the difference is about 2.5-4%, not 20-30%.**
- **Observations (descriptive only, NOT evidence for a cause):**
  - The daily minimum rose more than the daily peak (+3.8% vs. +2.4%). A rising baseline is the pattern a roughly constant added load would produce, but warmer nights in 2026 would also raise the minimum, so weather has to be accounted for before reading anything into it.
  - Weekdays and weekends differ little (peak +2.42% vs. +2.28%), a small gap on 26-27 weekend days. Dr. Holloway suggested data centers might show a weekday-daytime pattern; this table shows nothing clear either way.
- **Not yet done:** the same comparison adjusted for weather (needs the NASA POWER pull, Stage 4/5). Until then, do not attribute the difference to data centers, air conditioning or anything else.
- **Effect on the plan:** the year-to-year level shift in the models is about 2.5 GW, not the tens of GW I earlier feared. It is still comparable in size to the effect being tested (humidity), so how to handle it must still be decided before fitting any model, with Dr. Holloway.

## 2026-10-27 | Phase 4 | Project focus decided; weather points; NASA POWER time standard

### Focus decision (Dr. Holloway)
- **Approved framing (reported 2026-10-27):** combine the humidity question with the ISO-forecast benchmark. Main question: how close can an open model built on NASA POWER weather get to MISO's own day-ahead load forecast, and does adding humidity (dew point, later Heat Index) help? The 2025-to-2026 load difference is a **secondary** question using the same data.
- [Record her answer on whether she means predicting load from OBSERVED weather or forecasting ahead.]
- **Consequence for the paper:** POWER is reanalysis (weather that already happened), so my models predict load GIVEN the weather. MISO's forecast also has to predict the weather. The comparison therefore favors my models, and the paper must say so.
- **Claim to verify before citing:** that MISO's load forecasts already use dew point (seen in a summary of a MISO presentation, not yet checked at the source). Until verified, humidity is framed as a question we test, not as something operators miss.
- **MISO forecast data:** not yet pulled. Wait until the Grid Status monthly row quota resets on 2026-11-01. First list the MISO load forecast datasets, read their metadata (resolution, date range, columns) and estimate the row cost.

### Weather points (proposed; confirm final list)
- Rule: the number of points per MISO zone group follows the zone's share of load in the MISO report file (hour ending 1, 2025-07-14; one overnight hour, so approximate): LRZ1 15.9%, LRZ2_7 24.3%, LRZ3_5 13.4%, LRZ4 6.3%, LRZ6 13.2%, LRZ8_9_10 27.0%. Within each group, the largest or best-known MISO load center. City-to-zone assignments are from memory; check against MISO's zone map.
- Points: Minneapolis (44.98, -93.27); Milwaukee (43.04, -87.91); Detroit (42.33, -83.05); St. Louis (38.63, -90.20); Des Moines (41.59, -93.62); Indianapolis (39.77, -86.16); New Orleans (29.95, -90.07); Little Rock (34.75, -92.29).
- Chicago was in the original suggestion but is excluded: ComEd (northern Illinois) is in PJM, not MISO. [Verify on MISO's map.]
- Madison, WI (43.07, -89.40) considered. [Record decision: swap for Milwaukee, add as a 9th point, or leave out, and the reason.]
- Check that no two points fall in the same POWER grid cell (0.5 deg latitude x 0.625 deg longitude).
- Chosen BEFORE seeing any weather-vs-load results, so the selection cannot be tuned to the results.
- Simple mean across points for now; population or load weighting is a Phase 6 item.

### NASA POWER facts
- **Time standard (checked in the rOpenSci `nasapower` documentation; the official POWER page was blocked from my tool):** `time_standard` accepts UTC or LST (local solar time), and the **default is LST**. Request UTC explicitly, otherwise the weather is shifted by several hours against the UTC load data.
- Community choice affects parameter units. Hourly queries allow at most 15 parameters per query. The API throttles rapid repeated requests; exact limits not stated there.
- **Not yet verified (read the official page: power.larc.nasa.gov/docs/services/api/temporal/hourly/):** endpoint URL, exact parameter names for T2M, T2MDEW and RH2M at hourly resolution, units for the chosen community, missing-value code (I believe -999, unconfirmed), date range limit per request, and the latest available date.
- **Check after the first pull:** daily temperature should peak at about 20-22 UTC for the central US in summer (about 3-5 p.m. Central). If the raw data instead peaks around hour 14-16, it is in local solar time, not UTC.
- Raw pulls are saved to `data/raw/` as received, one file per point and year, before any processing.