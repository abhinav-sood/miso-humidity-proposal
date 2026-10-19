import os
import sys
from pathlib import Path

import pandas as pd
from dotenv import load_dotenv
from gridstatusio import GridStatusClient

load_dotenv()


api_key = os.getenv("GRID_STATUS_API_KEY")
if api_key is None:
    sys.exit("Could not find GRID_STATUS_API_KEY in .env")

client = GridStatusClient(api_key=api_key)


PROJECT_ROOT = Path(__file__).resolve().parent.parent   
RAW_DIR = PROJECT_ROOT / "data" / "raw"
RAW_DIR.mkdir(parents=True, exist_ok=True)


PULLS = {
    2025: ("2025-05-29 00:00", "2025-09-03 00:00"),
    2026: ("2026-05-29 00:00", "2026-09-03 00:00"),
}


usage_before = client.get_api_usage()["current_period_usage"]
print("Rows used before:", usage_before["total_api_rows_returned"])


meta = client.get_dataset_metadata("miso_load")
print("Earliest available (UTC):", meta.get("earliest_available_time_utc"))
print("Columns:", [c["name"] for c in meta["all_columns"]])

for year, (start, end) in PULLS.items():
    out_file = RAW_DIR / f"miso_load_{year}_raw.csv"

    if out_file.exists():
        print(f"{year}: {out_file.name} already exists, skipping pull")
        continue

    df = client.get_dataset(dataset="miso_load", start=start, end=end)

    df.to_csv(out_file, index=False)
    print(f"{year}: saved {len(df)} rows to {out_file}")

    print(df.head(3))
    print(df.tail(3))

usage_after = client.get_api_usage()["current_period_usage"]
print("Rows used after:", usage_after["total_api_rows_returned"])
print("Rows spent this run:",
      usage_after["total_api_rows_returned"] - usage_before["total_api_rows_returned"])