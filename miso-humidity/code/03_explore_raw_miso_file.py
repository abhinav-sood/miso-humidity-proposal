"""
03_fill_from_miso.py

Fills missing hours in the Grid Status hourly load using MISO's own report
"Forecasted and Actual Load Report" (the "_df_al" files on docs.misoenergy.org).
This follows Dr. Holloway's instruction to fill gaps directly from MISO reports.

Reads:   data/processed/hourly_load_utc_{2025,2026}.csv       (from 02_prepare_load.py)
Downloads (once, then cached): data/raw/miso_reports/{YYYYMMDD}_df_al.xls
Writes:  data/processed/hourly_load_filled_utc_{2025,2026}.csv
         outputs/tables/miso_validation_hours.csv   (hour-by-hour comparison, all tested shifts)
         outputs/tables/miso_validation_summary.csv
         outputs/tables/miso_fill_log.csv           (every hour that was filled, and from where)

What we learned about the MISO file (from the two files inspected on 2026-10-22):
  * Each file dated D+1 holds ACTUAL load for market day D only. The other six days in the
    file are forecast-only. So market day D comes from the file dated D+1.
  * Column "MISO ActualLoad (MWh)" is the system total (the six zone columns add up to it).
  * HourEnding runs 1-24; hour-ending h covers [h-1, h). Values are MWh per hour = average MW.
  * MISO's clock is believed to be fixed EST (UTC-5) all year. This is NOT stated in the file,
    so this script TESTS it against Grid Status before filling anything.

Safety: nothing is filled unless the validation step passes. If validation fails the script
stops, writes the comparison tables, and leaves the data unfilled.
Existing Grid Status values are never overwritten. Raw files are never modified.
"""

import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd
import requests

PROJECT_ROOT = Path(__file__).resolve().parent.parent
PROC_DIR = PROJECT_ROOT / "data" / "processed"
MISO_DIR = PROJECT_ROOT / "data" / "raw" / "miso_reports"
TABLE_DIR = PROJECT_ROOT / "outputs" / "tables"
MISO_DIR.mkdir(parents=True, exist_ok=True)
TABLE_DIR.mkdir(parents=True, exist_ok=True)

YEARS = [2025, 2026]
URL = "https://docs.misoenergy.org/marketreports/{d}_df_al.xls"
LOAD_COL = "MISO ActualLoad (MWh)"
ZONE_COLS = [
    "LRZ1 ActualLoad (MWh)", "LRZ2_7 ActualLoad (MWh)", "LRZ3_5 ActualLoad (MWh)",
    "LRZ4 ActualLoad (MWh)", "LRZ6 ActualLoad (MWh)", "LRZ8_9_10 ActualLoad (MWh)",
]
MISO_TZ = "Etc/GMT+5"        # fixed UTC-5 (EST all year). POSIX naming flips the sign.
LOCAL_TZ = "America/Chicago"  # the "day" used in this project

# --- Validation settings. Set BEFORE looking at the comparison; log them in LOG.md. ---
# Validation days: the 15th of June, July and August in each year (a fixed rule, not hand-picked).
VALIDATION_DAYS = [f"{y}-{m:02d}-15" for y in YEARS for m in (6, 7, 8)]
SHIFTS_TO_TEST = range(-3, 4)   # hours; the documented convention is shift 0
MEDIAN_ABS_PCT_MAX = 1.0        # typical hour must agree within 1%
P95_ABS_PCT_MAX = 3.0           # 95% of hours must agree within 3%
MIN_OVERLAP_HOURS = 72          # need at least 3 days' worth of comparable hours


def report_path(market_day: pd.Timestamp) -> Path:
    """Market day D is published in the file dated D+1."""
    file_date = (market_day + pd.Timedelta(days=1)).strftime("%Y%m%d")
    return MISO_DIR / f"{file_date}_df_al.xls"


def get_report(market_day: pd.Timestamp):
    """Return the local path of the report holding actuals for market_day (download once)."""
    path = report_path(market_day)
    if path.exists():
        return path
    url = URL.format(d=path.name[:8])
    try:
        r = requests.get(url, headers={"User-Agent": "Mozilla/5.0"}, timeout=60)
    except requests.RequestException as e:
        print(f"  download error for {url}: {e}")
        return None
    time.sleep(0.5)  # be polite to the server
    if r.status_code != 200:
        print(f"  {url} returned status {r.status_code}")
        return None
    path.write_bytes(r.content)
    return path


def read_market_day(path: Path, market_day: pd.Timestamp):
    """
    Read one report and return (Series of MW indexed by UTC hour start, reason).
    Returns (None, reason) if the day cannot be trusted.
    """
    df = pd.read_excel(path, header=4)   # column names are in the 5th row of the sheet

    needed = ["Market Day", "HourEnding", LOAD_COL] + ZONE_COLS
    missing_cols = [c for c in needed if c not in df.columns]
    if missing_cols:
        raise RuntimeError(f"{path.name}: expected columns not found: {missing_cols}\n"
                           f"Columns present: {list(df.columns)}")

    # keep only real hourly rows (drops the day-label rows and the disclaimer row)
    df["HourEnding"] = pd.to_numeric(df["HourEnding"], errors="coerce")
    df = df.dropna(subset=["HourEnding"]).copy()
    df["Market Day"] = pd.to_datetime(df["Market Day"], errors="coerce")
    for c in [LOAD_COL] + ZONE_COLS:
        df[c] = pd.to_numeric(df[c], errors="coerce")

    day = df[(df["Market Day"] == market_day) & df[LOAD_COL].notna()].copy()
    he = day["HourEnding"].astype(int)
    if len(day) != 24 or sorted(he) != list(range(1, 25)):
        return None, f"{len(day)} actual hours found for {market_day.date()}, expected 24"

    # sanity check: the six zones should add up to the system total
    rel_err = ((day[ZONE_COLS].sum(axis=1) - day[LOAD_COL]).abs() / day[LOAD_COL]).max()
    if rel_err > 1e-3:
        return None, f"zones do not add up to the MISO total (max relative error {rel_err:.4f})"

    # hour-ending h covers [h-1, h) in MISO clock time -> start = day + (h-1) hours
    start_miso = pd.Timestamp(market_day).tz_localize(MISO_TZ) + pd.to_timedelta(he.to_numpy() - 1, unit="h")
    idx = pd.DatetimeIndex(start_miso).tz_convert("UTC")
    return pd.Series(day[LOAD_COL].to_numpy(), index=idx, name="miso_mw").sort_index(), "ok"


def load_hourly(year: int) -> pd.DataFrame:
    path = PROC_DIR / f"hourly_load_utc_{year}.csv"
    if not path.exists():
        sys.exit(f"Missing {path}. Run 02_prepare_load.py first.")
    df = pd.read_csv(path, index_col="hour_utc", parse_dates=["hour_utc"])
    df.index = df.index.tz_convert("UTC")
    return df


hourly = {y: load_hourly(y) for y in YEARS}

# ======================================================================================
# STEP 1: VALIDATE. Does MISO's report agree with Grid Status, and is the hour convention right?
# ======================================================================================
print("STEP 1: validating MISO report against Grid Status")
rows = []
days_used = 0
for vd in VALIDATION_DAYS:
    md = pd.Timestamp(vd)
    path = get_report(md)
    if path is None:
        print(f"  {vd}: report unavailable, skipped")
        continue
    miso, reason = read_market_day(path, md)
    if miso is None:
        print(f"  {vd}: skipped ({reason})")
        continue
    days_used += 1
    gs = hourly[md.year]["load_mean"]
    for shift in SHIFTS_TO_TEST:
        shifted = miso.copy()
        shifted.index = shifted.index + pd.Timedelta(hours=shift)
        both = pd.concat([shifted.rename("miso_mw"), gs.rename("gridstatus_mw")], axis=1, join="inner").dropna()
        both["pct_diff"] = (both["miso_mw"] - both["gridstatus_mw"]) / both["gridstatus_mw"] * 100
        both["shift_hours"] = shift
        both["market_day"] = vd
        rows.append(both.reset_index().rename(columns={"index": "hour_utc"}))

if not rows:
    sys.exit("No validation day could be read. Nothing was filled. Check the download messages above.")

val = pd.concat(rows, ignore_index=True)
val.to_csv(TABLE_DIR / "miso_validation_hours.csv", index=False)

summary = val.groupby("shift_hours")["pct_diff"].agg(
    n_hours="count",
    mean_signed_pct="mean",
    median_abs_pct=lambda s: s.abs().median(),
    p95_abs_pct=lambda s: s.abs().quantile(0.95),
    max_abs_pct=lambda s: s.abs().max(),
).round(3)
summary.to_csv(TABLE_DIR / "miso_validation_summary.csv")
print(f"\nValidation used {days_used} of {len(VALIDATION_DAYS)} days. "
      f"Percent difference = (MISO - Grid Status) / Grid Status.")
print(summary.to_string())

best_shift = int(summary["median_abs_pct"].idxmin())
at0 = summary.loc[0]
checks = {
    "documented hour convention (shift 0) fits best": best_shift == 0,
    f"enough overlapping hours (>= {MIN_OVERLAP_HOURS})": at0["n_hours"] >= MIN_OVERLAP_HOURS,
    f"median abs difference <= {MEDIAN_ABS_PCT_MAX}%": at0["median_abs_pct"] <= MEDIAN_ABS_PCT_MAX,
    f"95th percentile abs difference <= {P95_ABS_PCT_MAX}%": at0["p95_abs_pct"] <= P95_ABS_PCT_MAX,
}
print("\nValidation checks:")
for name, ok in checks.items():
    print(f"  [{'PASS' if ok else 'FAIL'}] {name}")
if not all(checks.values()):
    sys.exit("\nSTOPPED: validation failed, so NOTHING was filled. "
             "Look at outputs/tables/miso_validation_summary.csv, log what you see, and ask Dr. Holloway.")
print("Validation passed. Systematic bias at shift 0 (mean signed %): "
      f"{at0['mean_signed_pct']:.3f}  <- log this number in LOG.md")

# ======================================================================================
# STEP 2: FILL. Only hours that are empty in Grid Status, only inside the study window.
# ======================================================================================
print("\nSTEP 2: filling missing hours")
fill_rows = []
for year in YEARS:
    df = hourly[year].copy()
    df["load_filled"] = df["load_mean"]
    df["source"] = np.where(df["load_mean"].notna(), "gridstatus", "missing")

    local = df.index.tz_convert(LOCAL_TZ)
    in_window = (local >= pd.Timestamp(f"{year}-06-01", tz=LOCAL_TZ)) & \
                (local < pd.Timestamp(f"{year}-09-01", tz=LOCAL_TZ))
    need = df.index[in_window & df["load_mean"].isna()]
    print(f"{year}: {len(need)} empty hours inside the June 1 - Aug 31 window")

    # group the needed hours by MISO market day, so each report is read once
    need_df = pd.DataFrame({"hour_utc": need})
    need_df["market_day"] = need_df["hour_utc"].dt.tz_convert(MISO_TZ).dt.tz_localize(None).dt.normalize()

    for md, grp in need_df.groupby("market_day"):
        path = get_report(md)
        if path is None:
            print(f"  {md.date()}: report unavailable, {len(grp)} hours stay missing")
            continue
        miso, reason = read_market_day(path, md)
        if miso is None:
            print(f"  {md.date()}: not used ({reason}), {len(grp)} hours stay missing")
            continue
        for h in grp["hour_utc"]:
            if h in miso.index:
                had_partial = df.at[h, "n_readings"] > 0
                df.at[h, "load_filled"] = miso.loc[h]
                df.at[h, "source"] = "miso_dfal"
                fill_rows.append({
                    "year": year, "hour_utc": h, "hour_local": h.tz_convert(LOCAL_TZ),
                    "market_day": md.date(), "miso_mw": miso.loc[h],
                    "replaced_partial_gridstatus_hour": bool(had_partial),
                    "gridstatus_readings_in_hour": int(df.at[h, "n_readings"]),
                })

    still = int((in_window & df["load_filled"].isna()).sum())
    filled = int((df["source"] == "miso_dfal").sum())
    print(f"  filled from MISO: {filled} | still missing in window: {still}")

    out = PROC_DIR / f"hourly_load_filled_utc_{year}.csv"
    df[["n_readings", "load_mean", "load_filled", "source"]].to_csv(out)
    print(f"  saved {out.name}")

pd.DataFrame(fill_rows).to_csv(TABLE_DIR / "miso_fill_log.csv", index=False)
print(f"\nFill log: {len(fill_rows)} hours -> outputs/tables/miso_fill_log.csv")