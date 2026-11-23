"""
09_build_features.py

Builds the model tables: one row per Central day with the target (daily peak load), the weather
features, the calendar features, and MISO's day-ahead forecast peak for the same day.

Reads:   data/processed/daily_merged.csv          (from 06_merge.py)
         data/processed/daily_miso_forecast.csv   (from 08_forecast_daily.py)
Writes:  data/processed/model_table_same_day.csv      weather of day D predicts the peak of day D
         data/processed/model_table_day_before.csv    weather of day D-1 predicts the peak of day D
         outputs/tables/feature_notes.csv

Design decisions, fixed BEFORE any model results existed (see LOG.md, 2026-11-23):
  * Two versions of the weather timing:
      same_day    - the weather that actually happened on day D. This has information a real forecaster
                    would not have on D-1, so it is a best case ("upper bound").
      day_before  - the weather of day D-1 only. This is a real forecast-style setup (everything is known
                    the day before) and is the MAIN comparison with MISO's day-ahead forecast.
  * Calendar features (day of week, holiday) belong to day D in both versions; they are known in advance.
  * Weather features: daily high temperature (tmax), mean specific humidity (qv_mean, used instead of dew
    point, see LOG.md), mean sunlight, mean wind, total rain; engineered: previous day's tmax and the number
    of consecutive hot days ending that day.
  * "Hot day" threshold = the 75th percentile of tmax in the TRAINING summer (2025) only, so nothing from
    the test summer is used to define it.
  * Every model sees exactly the same days: the first 2 days of each summer are dropped (they have no
    day-before / two-days-before weather inside the window), days that are not usable (a missing load
    hour), and days with incomplete solar data (2026-08-31, NASA solar is missing for its last 5 hours).
"""

import sys
from pathlib import Path

import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parent.parent
PROC_DIR = PROJECT_ROOT / "data" / "processed"
TABLE_DIR = PROJECT_ROOT / "outputs" / "tables"
TABLE_DIR.mkdir(parents=True, exist_ok=True)

TRAIN_YEAR = 2025
WEATHER_COLS = ["tmax", "qv_mean", "solar_mean", "ws_mean", "precip_sum"]
HOT_QUANTILE = 0.75

# US federal holidays inside June-August. Juneteenth (June 19) and Independence Day (July 4).
# July 4, 2026 is a Saturday, so the federal holiday is observed on Friday July 3: both dates are flagged.
HOLIDAYS = pd.to_datetime(["2025-06-19", "2025-07-04", "2026-06-19", "2026-07-03", "2026-07-04"])

# --------------------------------------------------------------------------------------
# Read
# --------------------------------------------------------------------------------------
daily_path = PROC_DIR / "daily_merged.csv"
fc_path = PROC_DIR / "daily_miso_forecast.csv"
for p in (daily_path, fc_path):
    if not p.exists():
        sys.exit(f"Missing {p}. Run 06_merge.py and 08_forecast_daily.py first.")

daily = pd.read_csv(daily_path, index_col="local_day", parse_dates=["local_day"]).sort_index()
fc = pd.read_csv(fc_path, index_col="local_day", parse_dates=["local_day"]).sort_index()

need = WEATHER_COLS + ["peak_mw", "usable", "year", "day_of_week", "solar_hours"]
missing_cols = [c for c in need if c not in daily.columns]
if missing_cols:
    sys.exit(f"daily_merged.csv is missing columns {missing_cols}. Re-run 06_merge.py (the version with the new NASA variables).")
assert daily.index.is_unique, "duplicate days in daily_merged.csv"
for y, n in daily.groupby("year").size().items():
    print(f"{y}: {n} days in daily_merged.csv")
    assert n == 92, f"{y}: expected 92 days"

# --------------------------------------------------------------------------------------
# Hot-day threshold from the training summer only, then the heat streak (consecutive hot days)
# --------------------------------------------------------------------------------------
hot_c = daily.loc[daily["year"] == TRAIN_YEAR, "tmax"].quantile(HOT_QUANTILE)
daily["hot"] = (daily["tmax"] >= hot_c).astype(int)

streak = pd.Series(0, index=daily.index, dtype=int)
for y in sorted(daily["year"].unique()):
    run = 0
    for day in daily.index[daily["year"] == y]:
        run = run + 1 if daily.at[day, "hot"] == 1 else 0
        streak.at[day] = run
daily["heat_streak"] = streak

# --------------------------------------------------------------------------------------
# Model tables
# --------------------------------------------------------------------------------------
def build_table(lag: int) -> pd.DataFrame:
    """lag 0 = same-day weather, lag 1 = day-before weather. Shifts are done WITHIN each summer."""
    t = pd.DataFrame(index=daily.index)
    t["year"] = daily["year"]
    t["peak_mw"] = daily["peak_mw"]
    for c in WEATHER_COLS + ["heat_streak"]:
        t[c] = daily.groupby("year")[c].shift(lag)
    t["tmax_prev"] = daily.groupby("year")["tmax"].shift(lag + 1)      # the day before the weather day
    t["holiday"] = daily.index.isin(HOLIDAYS).astype(int)
    for d in range(1, 7):                                              # Monday (0) is the baseline
        t[f"dow_{d}"] = (daily["day_of_week"] == d).astype(int)
    t["forecast_peak_mw"] = fc["forecast_peak_mw"].reindex(daily.index)
    return t


position = daily.groupby("year").cumcount()          # 0 for June 1, 1 for June 2, ...
reason = pd.Series("", index=daily.index)
reason[position < 2] = "first 2 days of the summer (no lagged weather)"
reason[~daily["usable"].astype(bool)] = "not usable (missing load hour)"
reason[daily["solar_hours"] < 24] = "incomplete NASA solar data"
keep = reason == ""

notes = [("hot_day_threshold_C_(75th_pct_of_2025_tmax)", round(float(hot_c), 3))]
for name, lag in [("same_day", 0), ("day_before", 1)]:
    t = build_table(lag)[keep]
    feat_cols = [c for c in t.columns if c not in ("year", "peak_mw", "forecast_peak_mw")]
    assert not t[feat_cols].isna().any().any(), "NaN in features"
    n_fc_missing = int(t["forecast_peak_mw"].isna().sum())
    assert n_fc_missing == 0, f"{n_fc_missing} days have no MISO forecast peak"
    out = PROC_DIR / f"model_table_{name}.csv"
    t.to_csv(out)
    per_year = t.groupby("year").size().to_dict()
    print(f"{name}: {len(t)} days {per_year} -> {out.name}")
    notes.append((f"rows_{name}", len(t)))

dropped = reason[reason != ""]
print("\nDays left out of every model (same days for every model):")
for day, why in dropped.items():
    print(f"  {day.date()}: {why}")
notes.append(("days_left_out", len(dropped)))
pd.DataFrame(notes, columns=["item", "value"]).to_csv(TABLE_DIR / "feature_notes.csv", index=False)
print(f"\nHot-day threshold (75th percentile of 2025 tmax): {hot_c:.2f} C")
print("Saved model tables and outputs/tables/feature_notes.csv")
