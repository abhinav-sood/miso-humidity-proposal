"""
08_forecast_daily.py

Turns MISO's saved load forecast files into ONE daily number per Central day: the forecast daily peak.

Reads:   data/raw/miso_forecast_mid_term_{2025,2026}_raw.csv      (from 07_pull_gridstatus_forecast.py)
Writes:  data/processed/daily_miso_forecast.csv

Rules (set before any model results; see LOG.md):
  * Every hour has about 7 forecast versions (one published per day). The DAY-AHEAD forecast is the LATEST
    version of each hour. 07b_inspect_forecast.py showed the latest version is published 24-47 hours before
    the hour it forecasts, so it never uses same-day information.
  * MISO-wide forecast for an hour = the sum of the 10 zones (Z1-Z10) of that version.
  * Convert to US Central time, keep June 1 - Aug 31 (92 days x 24 hours), as for actual load.
  * Forecast daily peak = highest forecast hour of the Central day. It is the same definition as the actual
    daily peak (highest hourly value), so the two are directly comparable.
"""

from pathlib import Path

import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parent.parent
RAW_DIR = PROJECT_ROOT / "data" / "raw"
PROC_DIR = PROJECT_ROOT / "data" / "processed"
PROC_DIR.mkdir(parents=True, exist_ok=True)
LOCAL_TZ = "America/Chicago"
N_ZONES = 10

tables = []
for year in [2025, 2026]:
    path = RAW_DIR / f"miso_forecast_mid_term_{year}_raw.csv"
    if not path.exists():
        raise SystemExit(f"Missing {path}. Run 07_pull_gridstatus_forecast.py first.")
    df = pd.read_csv(path, parse_dates=["interval_start_utc", "publish_time_utc"])

    # keep only the latest version of each target hour (the day-ahead rule)
    latest = df.groupby("interval_start_utc")["publish_time_utc"].transform("max")
    df = df[df["publish_time_utc"] == latest]
    assert len(df) == df["interval_start_utc"].nunique() * N_ZONES, "expected 10 zones per hour"
    assert not df["load_forecast"].isna().any(), "missing forecast values"

    lead_h = (df["interval_start_utc"] - df["publish_time_utc"]).dt.total_seconds() / 3600
    print(f"{year}: hours between the version used and the hour forecast: min {lead_h.min():.0f}, max {lead_h.max():.0f}")

    # MISO-wide forecast = sum of the 10 zones
    hourly = df.groupby("interval_start_utc")["load_forecast"].sum().to_frame("forecast_mw")

    # to Central time, June 1 - Aug 31 only
    hourly.index = hourly.index.tz_convert(LOCAL_TZ)
    start = pd.Timestamp(f"{year}-06-01", tz=LOCAL_TZ)
    end = pd.Timestamp(f"{year}-09-01", tz=LOCAL_TZ)          # exclusive
    hourly = hourly[(hourly.index >= start) & (hourly.index < end)].copy()
    assert len(hourly) == 92 * 24, f"{year}: expected {92 * 24} hours, found {len(hourly)}"

    # daily forecast peak = highest forecast hour of each Central day
    hourly["day"] = hourly.index.normalize()
    g = hourly.groupby("day")["forecast_mw"]
    daily = pd.DataFrame({
        "forecast_peak_mw": g.max(),
        "forecast_mean_mw": g.mean(),
        "n_hours": g.count(),
    })
    assert (daily["n_hours"] == 24).all(), "a day with fewer than 24 forecast hours"
    daily.index = daily.index.tz_localize(None)
    daily.index.name = "local_day"
    daily["year"] = year
    print(year, "days:", len(daily), "| mean forecast peak (MW):", round(daily["forecast_peak_mw"].mean()))
    tables.append(daily)

out = pd.concat(tables)
out.to_csv(PROC_DIR / "daily_miso_forecast.csv")
print("saved daily_miso_forecast.csv", out.shape)
