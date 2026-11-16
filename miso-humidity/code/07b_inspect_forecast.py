from pathlib import Path
import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parent.parent
RAW_DIR = PROJECT_ROOT / "data" / "raw"

for year in [2025, 2026]:
    path = RAW_DIR / f"miso_forecast_mid_term_{year}_raw.csv"
    df = pd.read_csv(path, parse_dates=["interval_start_utc", "interval_end_utc", "publish_time_utc"])

    print(f"\n=== {year} ===")
    print("rows:", len(df))
    print("zones:", sorted(df["lrz"].unique()))
    print("regions:", sorted(df["region"].unique()))
    print("publish times:", df["publish_time_utc"].nunique(),
          df["publish_time_utc"].min(), df["publish_time_utc"].max())
    print("missing load_forecast:", int(df["load_forecast"].isna().sum()))
    print("load_forecast per zone, min / max:", df["load_forecast"].min(), df["load_forecast"].max())

    key = ["interval_start_utc", "publish_time_utc", "lrz"]
    print("duplicate keys:", int(df.duplicated(key).sum()))

    print("zones per hour+version:")
    print(df.groupby(["interval_start_utc", "publish_time_utc"]).size().value_counts())

    print("versions per hour:")
    print(df.groupby("interval_start_utc")["publish_time_utc"].nunique().value_counts())


    one = df[(df["interval_start_utc"] == pd.Timestamp(f"{year}-06-15 20:00", tz="UTC"))
             & (df["publish_time_utc"] == pd.Timestamp(f"{year}-06-14 05:00", tz="UTC"))]
    print("zones in that slice:", len(one), "| MISO-wide sum (MW):", one["load_forecast"].sum())
    latest = df.groupby("interval_start_utc")["publish_time_utc"].max()
    lead_hours = (latest.index.to_series() - latest).dt.total_seconds() / 3600
    print("hours between latest version and target hour, min / max:",
        lead_hours.min(), lead_hours.max())