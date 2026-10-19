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

### Decisions to make before Stage 2 (set before looking at any hourly results)
1. Which hour a reading belongs to (proposal: `interval_start_utc` rounded down to the hour).
2. How to combine the 12 readings in an hour (proposal: mean). Note that "daily peak" will then mean the highest hourly mean, not the highest instantaneous reading.
3. Minimum readings per hour to keep an hour (proposal: a threshold such as 9 of 12, with others marked missing). [Record my chosen threshold and why.]

- **Affects:** Stage 2 (hourly aggregation, daily table), and the number of usable days in 2025.