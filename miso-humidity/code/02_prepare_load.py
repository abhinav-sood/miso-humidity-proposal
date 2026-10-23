"""
02_prepare_load.py

Turns the raw 5-minute Grid Status load files into clean HOURLY tables (still in UTC).

Reads:   data/raw/miso_load_2025_raw.csv, data/raw/miso_load_2026_raw.csv
Writes:  data/processed/hourly_load_utc_2025.csv, data/processed/hourly_load_utc_2026.csv

Rules (decided 2026-10-20, before looking at any hourly results; see LOG.md):
  1. A 5-minute reading belongs to the hour of its interval_start_utc, rounded down.
  2. Hourly load = mean of the readings that are present in that hour (MW).
  3. An hour needs at least 9 of its 12 readings, otherwise load_mean is left empty (NaN).
     Empty hours are NOT filled here; 03_fill_from_miso.py does that.
Hours with no readings at all (like the 2.6-day hole in 2025) are added back as empty
rows, so every hour from the first to the last appears exactly once.

Everything stays in UTC. The conversion to Central time happens in 04_daily_table.py.
Raw files are never modified.
"""

import sys
from pathlib import Path

import numpy as np
import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parent.parent
RAW_DIR = PROJECT_ROOT / "data" / "raw"
OUT_DIR = PROJECT_ROOT / "data" / "processed"
OUT_DIR.mkdir(parents=True, exist_ok=True)

YEARS = [2025, 2026]
MIN_READINGS = 9          # rule 3
READINGS_PER_HOUR = 12    # 60 minutes / 5 minutes


def build_hourly(year: int) -> pd.DataFrame:
    path = RAW_DIR / f"miso_load_{year}_raw.csv"
    if not path.exists():
        sys.exit(f"Missing raw file: {path}")

    raw = pd.read_csv(path, parse_dates=["interval_start_utc", "interval_end_utc"])

    # --- sanity checks on the raw data (stop loudly if something is off) ---
    if raw["interval_start_utc"].dt.tz is None:
        sys.exit(f"{year}: timestamps have no time zone. Expected UTC.")
    raw["interval_start_utc"] = raw["interval_start_utc"].dt.tz_convert("UTC")
    if raw["interval_start_utc"].duplicated().any():
        sys.exit(f"{year}: duplicate timestamps found.")
    if (raw["load"] <= 0).any():
        sys.exit(f"{year}: zero or negative load values found.")

    # rule 1: assign each reading to its hour (start time, rounded down)
    raw["hour_utc"] = raw["interval_start_utc"].dt.floor("h")

    # rule 2: hourly mean of the readings present
    hourly = raw.groupby("hour_utc").agg(
        n_readings=("load", "count"),
        load_mean=("load", "mean"),
    )

    # rule 3: require at least 9 of 12 readings
    hourly.loc[hourly["n_readings"] < MIN_READINGS, "load_mean"] = np.nan

    # put completely absent hours back in as empty rows
    full_hours = pd.date_range(hourly.index.min(), hourly.index.max(), freq="h")
    hourly = hourly.reindex(full_hours)
    hourly.index.name = "hour_utc"
    hourly["n_readings"] = hourly["n_readings"].fillna(0).astype(int)

    return hourly


for year in YEARS:
    hourly = build_hourly(year)

    n_rows = len(hourly)
    n_valid = int(hourly["load_mean"].notna().sum())
    n_absent = int((hourly["n_readings"] == 0).sum())
    n_dropped = int(((hourly["n_readings"] > 0) & (hourly["n_readings"] < MIN_READINGS)).sum())
    assert n_valid + n_absent + n_dropped == n_rows, "hour counts do not add up"

    print(f"{year}: {n_rows} hourly rows | valid: {n_valid} | "
          f"dropped by the 9-of-12 rule: {n_dropped} | completely absent: {n_absent}")
    print(f"      spread of readings per hour:\n{hourly['n_readings'].value_counts().sort_index().to_string()}")

    out_path = OUT_DIR / f"hourly_load_utc_{year}.csv"
    hourly.to_csv(out_path)
    print(f"      saved {out_path.name}")