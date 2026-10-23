import sys
from pathlib import Path

import pandas as pd
import requests

PROJECT_ROOT = Path(__file__).resolve().parent.parent
OUT_DIR = PROJECT_ROOT / "data" / "raw" / "miso_reports"
OUT_DIR.mkdir(parents=True, exist_ok=True)

# 20250715 should hold actuals for Jul 14, and 20250602 should hold actuals for Jun 1
DATES = ["20250715", "20250602"]
URL = "https://docs.misoenergy.org/marketreports/{d}_df_al.xls"
LOAD_COL = "MISO ActualLoad (MWh)"

for d in DATES:
    path = OUT_DIR / f"{d}_df_al.xls"
    if not path.exists():
        r = requests.get(URL.format(d=d), headers={"User-Agent": "Mozilla/5.0"}, timeout=60)
        if r.status_code != 200:
            sys.exit(f"{d}: download failed with status {r.status_code}")
        path.write_bytes(r.content)

    df = pd.read_excel(path, header=4)
    df["HourEnding"] = pd.to_numeric(df["HourEnding"], errors="coerce")
    df = df.dropna(subset=["HourEnding"])   # drops the day-label rows and the disclaimer row
    df["Market Day"] = pd.to_datetime(df["Market Day"])
    df[LOAD_COL] = pd.to_numeric(df[LOAD_COL], errors="coerce")

    print(f"\n===== {d} =====")
    print(df.groupby("Market Day")[LOAD_COL].agg(["count", "min", "max"]))