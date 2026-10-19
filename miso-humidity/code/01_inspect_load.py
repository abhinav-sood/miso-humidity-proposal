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