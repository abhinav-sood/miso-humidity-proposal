from gridstatusio import GridStatusClient
import os
from dotenv import load_dotenv
from datetime import datetime, timezone
import pandas as pd
import requests
import numpy as np

load_dotenv()
GRID_STATUS_API_KEY = os.getenv("GRID_STATUS_API_KEY")
grid_status_client = GridStatusClient(api_key = GRID_STATUS_API_KEY)

NASA_POWER_API_URL = "https://power.larc.nasa.gov/api/temporal"

#------PULL MISO LOAD DATA FOR MID TO ALTE JULY------------
print("Fetching MISO load data for Mid-July to Late-July...")
df_miso = grid_status_client.get_dataset(
    dataset = "miso_load",
    start = "2026-07-15 00:00",
    end = "2026-07-31 23:59",
    filter_column="load",
)#get the miso load from july 15th to july 31st(2026)

df_miso = df_miso[["interval_end_utc", "load"]].rename(columns={"interval_end_utc": "timestamp"})
df_miso["timestamp"] = pd.to_datetime(df_miso["timestamp"], utc = True)#parse to utc in datetime format
df_miso = df_miso.sort_values(by="timestamp", ascending=True)


#-----------FETCH WEATHER FROM NASA POWER(CHICAGO)-----------
request = f"{NASA_POWER_API_URL}/hourly/point?start=20260715&end=20260731&latitude=41.88&longitude=-87.62&community=re&parameters=T2M,RH2M&format=json"
response = requests.get(request)
NASA_POWER_HUMIDITY = {}

if response.status_code == 200:
    response_data = response.json()
    raw_power_data = response_data["properties"]["parameter"]
    rh_data = raw_power_data.get("RH2M", {})#humdity 2 meters
    t2m_data = raw_power_data.get("T2M", {})#temperature 2 meters

    weather_records = []
    for time_Str, rh_val in rh_data.items():
        try:
            dt = datetime.strptime(time_Str, "%Y%m%d%H").replace(tzinfo = timezone.utc)
            '''weather_records.append(
                {
                    "timestamp": dt,
                    "relative_humidity": rh_val if rh_val != -999.0 else np.nan,
                    "temp_c": t2m_data.get(time_Str, np.nan) if t2m_data.get(time_Str) != -999.0 else np.nan,
                }
                weather_records[0]["temp_f"] = weather_records[0].pop("temp_c")
            )'''
            
        
        except ValueError:
            continue

        for key in weather_records[0]["temp_f"]:
                        weather_records[0][key] = (9/5) * (weather_records[0][key]) + 32

        df_weather = (
        pd.DataFrame(weather_records)
        .assign(timestamp=lambda d: pd.to_datetime(d["timestamp"], utc=True))
        .sort_values(by="timestamp")
        .reset_index(drop=True)
    )
    
else:
    print(f"Failed to fetch NASA POWER data. Status code: {response.status_code}")



