import pandas as pd
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent   
RAW_DIR = PROJECT_ROOT / "data" / "raw"


raw_miso_2025_load_df = pd.read_csv(RAW_DIR / "miso_load_2025_raw.csv", parse_dates = ["interval_start_utc", "interval_end_utc"])
raw_miso_2026_load_df = pd.read_csv(RAW_DIR / "miso_load_2026_raw.csv", parse_dates = ["interval_start_utc", "interval_end_utc"])


'''print(raw_miso_2025_load_df.dtypes)
print(len(raw_miso_2025_load_df))
print(len(raw_miso_2026_load_df))
print(raw_miso_2025_load_df.head())
print(raw_miso_2026_load_df.head())'''


raw_miso_2025_load_df["time_diff"] = raw_miso_2025_load_df["interval_start_utc"].diff()
raw_miso_2026_load_df["time_diff"] = raw_miso_2026_load_df["interval_start_utc"].diff()

#print(raw_miso_2025_load_df["time_diff"].value_counts())
#print(raw_miso_2026_load_df["time_diff"].value_counts())

#finding the longest time gap
longest_gap_2025 = raw_miso_2025_load_df.loc[raw_miso_2025_load_df["time_diff"].dt.total_seconds() > 24*60*60]

miso_2025_max_load = raw_miso_2025_load_df["load"].max()
miso_2026_max_load = raw_miso_2026_load_df["load"].max()

miso_2025_min_load = raw_miso_2025_load_df["load"].min()
miso_2026_min_load = raw_miso_2026_load_df["load"].min()

miso_2025_zero_load_count = (raw_miso_2025_load_df["load"] == 0).sum()
miso_2026_zero_load_count = (raw_miso_2026_load_df["load"] == 0).sum()

print(f"2025 max load: {miso_2025_max_load}\n2026 max load: {miso_2026_max_load}\n2025 min load: {miso_2025_min_load}\n2026 min load: {miso_2026_min_load}\n2025 zero load count: {miso_2025_zero_load_count}\n2026 zero load count: {miso_2026_zero_load_count}\n")

raw_miso_2025_load_df["load_diff"] = raw_miso_2025_load_df["load"].diff().abs()
raw_miso_2026_load_df["load_diff"] = raw_miso_2026_load_df["load"].diff().abs()

max_diff_2025 = raw_miso_2025_load_df["load_diff"].max()
max_diff_2026 = raw_miso_2026_load_df["load_diff"].max()

row5_of_max_diff2025 = raw_miso_2025_load_df["load_diff"].idxmax()
row5_of_max_diff2026 = raw_miso_2026_load_df["load_diff"].idxmax()

print(f"5 rows surronding biggest jump in 2025: {raw_miso_2025_load_df.loc[row5_of_max_diff2025-5 : row5_of_max_diff2025+5, ["interval_start_utc", "load", "load_diff", "time_diff"]]}")
print(f"5 rows surronding biggest jump in 2026: {raw_miso_2026_load_df.loc[row5_of_max_diff2026-5 : row5_of_max_diff2026+5, ["interval_start_utc", "load", "load_diff", "time_diff"]]}")


print(f"max load diff for 2025: {max_diff_2025}")
print(f"max load diff for 2026: {max_diff_2026}")

raw_miso_2025_load_df["time_diff_5mins"] = (raw_miso_2025_load_df["time_diff"] == pd.Timedelta(minutes=5))
raw_miso_2026_load_df["time_diff_5mins"] = (raw_miso_2026_load_df["time_diff"] == pd.Timedelta(minutes=5))

print(f"number of 2025 rows that have 5 min intervals: {(raw_miso_2025_load_df["time_diff_5mins"] == True).sum()}")


is_5min_2025 = raw_miso_2025_load_df["time_diff"] == pd.Timedelta(minutes=5)
is_5min_2026 = raw_miso_2026_load_df["time_diff"] == pd.Timedelta(minutes=5)

real_diff_2025 = raw_miso_2025_load_df.loc[is_5min_2025, "load_diff"]
real_diff_2026 = raw_miso_2026_load_df.loc[is_5min_2026, "load_diff"]


print(f"2025 rows: {len(real_diff_2025)}  max: {real_diff_2025.max()}  median: {real_diff_2025.median()}  99th pct: {real_diff_2025.quantile(0.99)}")
print(f"2026 rows: {len(real_diff_2026)}  max: {real_diff_2026.max()}  median: {real_diff_2026.median()}  99th pct: {real_diff_2026.quantile(0.99)}")

i_2025 = real_diff_2025.idxmax()
i_2026 = real_diff_2026.idxmax()

cols = ["interval_start_utc", "load", "load_diff", "time_diff"]

print("Rows around the largest real 5-minute change, 2025:")
print(raw_miso_2025_load_df.loc[i_2025 - 5 : i_2025 + 5, cols])

print("Rows around the largest real 5-minute change, 2026:")
print(raw_miso_2026_load_df.loc[i_2026 - 5 : i_2026 + 5, cols])