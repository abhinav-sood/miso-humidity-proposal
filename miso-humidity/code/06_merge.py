import json
from pathlib import Path
import pandas as pd
import matplotlib
matplotlib.use("Agg")           
import matplotlib.pyplot as plt

PROJECT_ROOT = Path(__file__).resolve().parent.parent
POWER_DIR = PROJECT_ROOT / "data" / "raw" / "nasa_power_v2"
tables = []

for jsonFile in POWER_DIR.rglob("*.json"):
    with open(jsonFile, "r") as file:
        data = json.load(file)
        variables = data["properties"]["parameter"]
        df = pd.DataFrame(variables)
        df = df.replace(-999, float("nan"))
        df["hour_utc"] = pd.to_datetime(df.index, format="%Y%m%d%H").tz_localize("UTC")
        df["city"] = jsonFile.stem.replace("power_", "").rsplit("_", 1)[0]
        tables.append(df)

#each row is one city at one hour with T2M, RH2M, QV2M, ALLSKY_SFC_SW_DWN, WS2M and PRECTOTCORR
weather = pd.concat(tables)

#average to get one weather number per hour for all 8 cities(miso wide)        
weather_hourly = weather.groupby("hour_utc")[["T2M", "RH2M", "QV2M", "ALLSKY_SFC_SW_DWN", "WS2M", "PRECTOTCORR"]].mean()
print(weather_hourly.shape)
print(weather_hourly.isna().sum())
print(weather_hourly.tail(3))

#read the load
load_2025 = pd.read_csv(f"{PROJECT_ROOT}/data/processed/hourly_load_filled_utc_2025.csv", index_col="hour_utc",  parse_dates=["hour_utc"])



load_2026 = pd.read_csv(f"{PROJECT_ROOT}/data/processed/hourly_load_filled_utc_2026.csv", index_col="hour_utc",  parse_dates=["hour_utc"])

load = pd.concat([load_2025, load_2026])

assert load.index.is_unique

#join weather to load

merged = weather_hourly.join(load, how="inner")

merged.index = merged.index.tz_convert("America/Chicago")

merged = merged[merged.index.month.isin([6,7,8])].copy()

merged["day"] = merged.index.normalize()


#daily weather numbers


daily_weather = pd.DataFrame({
    "tmax":       merged.groupby("day")["T2M"].max(),
    "rh_mean":    merged.groupby("day")["RH2M"].mean(),
    "qv_mean":    merged.groupby("day")["QV2M"].mean(),
    "solar_mean": merged.groupby("day")["ALLSKY_SFC_SW_DWN"].mean(),
    "ws_mean":    merged.groupby("day")["WS2M"].mean(),
    "precip_sum": merged.groupby("day")["PRECTOTCORR"].sum(),
    "solar_hours": merged.groupby("day")["ALLSKY_SFC_SW_DWN"].count(),
})

print(daily_weather.shape)
print(daily_weather[daily_weather["solar_hours"] < 24])

daily_load = pd.read_csv(f"{PROJECT_ROOT}/data/processed/daily_load_all.csv", index_col = "local_day", parse_dates=["local_day"])
daily_weather.index = daily_weather.index.tz_localize(None)

#combine daily load and weather
daily = daily_load.join(daily_weather, how = "inner")
print(daily.shape)

daily.to_csv(f"{PROJECT_ROOT}/data/processed/daily_merged.csv")

use = daily[daily["usable"]]
print("usable days:", len(use))


FIG_DIR = PROJECT_ROOT / "outputs" / "figures"
FIG_DIR.mkdir(parents=True, exist_ok=True)

fig, ax = plt.subplots(figsize=(8, 5))
for year, color in [(2025, "#2a78d6"), (2026, "#eb6834")]:
    sub = use[use["year"] == year]
    ax.scatter(sub["tmax"], sub["peak_mw"] / 1000, s=22, alpha=0.8,
               color=color, label=str(year))

ax.set_xlabel("Daily high temperature (°C, 8-city mean)")
ax.set_ylabel("Daily peak load (GW)")
ax.set_title("MISO daily peak load vs. temperature, June-August")
ax.legend(frameon=False)
fig.tight_layout()
fig.savefig(FIG_DIR / "peak_vs_tmax.png", dpi=160)
plt.close(fig)
print("saved peak_vs_tmax.png")
