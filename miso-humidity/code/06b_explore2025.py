from pathlib import Path
import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parent.parent
daily = pd.read_csv(PROJECT_ROOT / "data" / "processed" / "daily_merged.csv",
                    index_col="local_day", parse_dates=["local_day"])

use = daily[daily["usable"]]
train = use[use["year"] == 2025]

cols = ["peak_mw", "tmax", "rh_mean", "qv_mean", "solar_mean", "ws_mean", "precip_sum"]
print(train[cols].corr().round(2))

print(use.groupby("year")[["tmax", "peak_mw"]].mean())