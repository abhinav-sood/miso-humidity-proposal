# Project Log

## 2026-10-14 | Phase 2 | Grid Status MISO load pull

- **What I did:** Pulled dataset `miso_load` for 2026-05-29 to 2026-09-02 and 2025-05-29 to 2025-09-02. The pull is padded past June 1 and Aug 31 so that edge hours are not lost when I convert time zones and trim later.
- **Dataset facts:** Grid Status describes `miso_load` as load in 5-minute intervals as reported by MISO. Row counts match that: 27,820 rows (2026) and 27,017 (2025). Hourly would have been about 2,300 per summer.
- **Problem 1:** The first run did not save the data to disk, so both pulls were lost when the script ended. Cost: about 54,800 rows. I re-pulled once, with a save step added.
- **Problem 2:** The first pull included `filter_column="load"` with no `filter_value`. The client documentation does not say what this does, so I removed it for the re-pull.
- **Observation:** Both summers have fewer rows than a full 97-day window at 5-minute spacing (about 27,936). 2026 is short by about 116, and 2025 by about 919. Cause not yet known. [Fill in after inspecting the saved files: where the gaps are.]
- **Usage:** Free plan, 500,000 rows/month, 250 requests/month, 50,000 rows per response. Before the re-pull: 187,289 rows and 31 requests used this period (period ends Nov 1). [Fill in usage after the re-pull.]
- **Open questions:** (1) What time zone does the API assume for my start and end strings (request showed `timezone: None`)? (2) Does resampling in the API reduce rows billed? (3) Why is 2025 missing about 919 rows?
- **Decision pending:** How to aggregate 5-minute load to hourly (mean vs. other). This will define "peak load" in the paper.
- **Affects:** data/raw/ files, the hourly aggregation step, and the daily peak calculation in Phase 3.