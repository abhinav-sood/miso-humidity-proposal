import pandas as pd
from pathlib import Path
import numpy as np

PROJECT_ROOT = Path(__file__).resolve().parent.parent   
RAW_DIR = PROJECT_ROOT / "data" / "raw"


raw_miso_2025_load_df = pd.read_csv(RAW_DIR / "miso_load_2025_raw.csv", parse_dates = ["interval_start_utc", "interval_end_utc"])
raw_miso_2026_load_df = pd.read_csv(RAW_DIR / "miso_load_2026_raw.csv", parse_dates = ["interval_start_utc", "interval_end_utc"])

raw_miso_2025_load_df["interval_start_utc_roundedDown"] = raw_miso_2025_load_df["interval_start_utc"].dt.floor("h")
raw_miso_2026_load_df["interval_start_utc_roundedDown"] = raw_miso_2026_load_df["interval_start_utc"].dt.floor("h")

hourly_2025 = raw_miso_2025_load_df.groupby("interval_start_utc_roundedDown").agg(
    n_readings=("load", "count"),
    load_mean=("load", "mean")
)

hourly_2026 = raw_miso_2026_load_df.groupby("interval_start_utc_roundedDown").agg(
    n_readings=("load", "count"),
    load_mean=("load", "mean")
)

print(f"Number of hourly rows in 2025: {len(hourly_2025)}")
print(f"Number of hourly rows in 2026: {len(hourly_2026)}")
print(f"Number of readings in 2025: {hourly_2025["n_readings"].value_counts()}")
print(f"Number of readings in 2026: {hourly_2026["n_readings"].value_counts()}")

#find the hours where there are 9 or more readings in an hour
hourly_2025["less_than_9_readings"] = (hourly_2025["n_readings"] < 9)
total_2025_8_below_values = hourly_2025["less_than_9_readings"].sum()

hourly_2026["less_than_9_readings"] = (hourly_2026["n_readings"] < 9)
total_2026_8_below_values = hourly_2026["less_than_9_readings"].sum()

print(f"Less than 9 readings in an hour 2025: {total_2025_8_below_values}")
print(f"Less than 9 readings in an hour 2026: {total_2026_8_below_values}")

#filter out any load values for an hour that has 9 or less readings
hourly_2025.loc[hourly_2025["less_than_9_readings"] == True, "load_mean"] = np.nan
hourly_2026.loc[hourly_2026["less_than_9_readings"] == True, "load_mean"] = np.nan
print(f"Total 2025 hours that have a value: {hourly_2025["load_mean"].notna().sum()}")
print(f"Total 2026 hours that have a value: {hourly_2026["load_mean"].notna().sum()}")

#put the completely absent hours back into the table as missing rows
full_hours_2025 = pd.date_range(start=hourly_2025.index.min(), end=hourly_2025.index.max(), freq="h")
full_hours_2026 = pd.date_range(start=hourly_2026.index.min(), end=hourly_2026.index.max(), freq="h")

hourly_2025 = hourly_2025.reindex(full_hours_2025)
hourly_2026 = hourly_2026.reindex(full_hours_2026)


print(f"2025 rows: {len(hourly_2025)}  missing hours: {hourly_2025['load_mean'].isna().sum()}")
print(f"2026 rows: {len(hourly_2026)}  missing hours: {hourly_2026['load_mean'].isna().sum()}")


#convert utc to central time
hourly_2025 = hourly_2025.tz_convert('America/Chicago')
hourly_2026 = hourly_2026.tz_convert('America/Chicago')

filtered_hourly_2025 = hourly_2025.loc['2025-06-01':'2025-08-31']
filtered_hourly_2026 = hourly_2026.loc['2026-06-01':'2026-08-31']

for name, df in [("2025", filtered_hourly_2025), ("2026", filtered_hourly_2026)]:
    print(f"{name}: rows={len(df)}, first={df.index[0]}, last={df.index[-1]}, missing={df['load_mean'].isna().sum()}")