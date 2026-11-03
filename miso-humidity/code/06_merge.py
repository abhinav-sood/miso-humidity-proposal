import json
from pathlib import Path
import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parent.parent
POWER_DIR = PROJECT_ROOT / "data" / "raw" / "nasa_power"
tables = []

for jsonFile in POWER_DIR.rglob("*.json"):
    with open(jsonFile, "r") as file:
        data = json.load(file)
        variables = data["properties"]["parameter"]
        df = pd.DataFrame(variables)
        df["hour_utc"] = pd.to_datetime(df.index, format="%Y%m%d%H").tz_localize("UTC")
        df["city"] = jsonFile.stem.replace("power_", "").rsplit("_", 1)[0]
        tables.append(df)

#each row is one city at one hour with 52m, t2mdew, rh2m(%), hour_utc, city
weather = pd.concat(tables)

#average to get one weather number per hour for all 8 cities(miso wide)        
weather_hourly = weather.groupby("hour_utc")[["T2M", "T2MDEW", "RH2M"]].mean()

#read the load
load_2025 = pd.read_csv(f"{PROJECT_ROOT}/data/processed/hourly_load_filled_utc_2025.csv", index_col="hour_utc",  parse_dates=["hour_utc"])



load_2026 = load_2025 = pd.read_csv(f"{PROJECT_ROOT}/data/processed/hourly_load_filled_utc_2026.csv", index_col="hour_utc",  parse_dates=["hour_utc"])

load = pd.concat([load_2025, load_2026])

#join weather to load

merged = weather_hourly.join(load, how="inner")
