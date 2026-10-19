import pandas as pd
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent   
RAW_DIR = PROJECT_ROOT / "data" / "raw"


raw_miso_2025_load_df = pd.read_csv(RAW_DIR / "miso_load_2025_raw.csv", parse_dates = ["interval_start_utc", "interval_end_utc"])
raw_miso_2026_load_df = pd.read_csv(RAW_DIR / "miso_load_2026_raw.csv", parse_dates = ["interval_start_utc", "interval_end_utc"])


print(len(raw_miso_2025_load_df["load"]))
