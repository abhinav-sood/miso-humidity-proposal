import os
from pathlib import Path

import pandas as pd
from dotenv import load_dotenv
from gridstatusio import GridStatusClient

load_dotenv()
client = GridStatusClient(api_key=os.getenv("GRID_STATUS_API_KEY"))

PROJECT_ROOT = Path(__file__).resolve().parent.parent
RAW_DIR = PROJECT_ROOT / "data" / "raw"
DATASET = "miso_load_forecast_mid_term_by_region"

#june 1st to sept 2nd for 2025 and 2026
summers = [
    {"year": 2025, "start": "2025-06-01", "end": "2025-09-02"},
    {"year": 2026, "start": "2026-06-01", "end": "2026-09-02"},
]

print("before:", client.get_api_usage()["current_period_usage"])

for s in summers:
    out = RAW_DIR / f"miso_forecast_mid_term_{s['year']}_raw.csv"
    if out.exists():
        print(f"{out.name} already exists, skipping")
        continue
    df = client.get_dataset(dataset=DATASET, start=s["start"], end=s["end"])
    df.to_csv(out, index=False)          
    print(s["year"], "rows:", len(df))

print("after:", client.get_api_usage()["current_period_usage"])