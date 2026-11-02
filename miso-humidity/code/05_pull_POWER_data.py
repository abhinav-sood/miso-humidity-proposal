import requests
from pathlib import Path
import json
import os
import time



NASA_POWER_API_URL = "https://power.larc.nasa.gov/api/temporal"

cities = [
    {"name": "minneapolis",  "lat": 44.98, "lon": -93.27},
    {"name": "madison",    "lat": 43.07, "lon": -89.40},
    {"name": "detroit",      "lat": 42.33, "lon": -83.05},
    {"name": "st_louis",    "lat": 38.63, "lon": -90.20},
    {"name": "des_moines",   "lat": 41.59, "lon": -93.62},
    {"name": "indianapolis", "lat": 39.77, "lon": -86.16},
    {"name": "new_orleans",  "lat": 29.95, "lon": -90.07},
    {"name": "little_rock",  "lat": 34.75, "lon": -92.29},
]

summers = [
    {"year": 2025, "start": 20250529, "end": 20250902},
    {"year": 2026, "start": 20260529, "end": 20260902},
]

PROJECT_ROOT = Path(__file__).resolve().parent.parent
POWER_DIR = PROJECT_ROOT / "data" / "raw" / "nasa_power"
os.makedirs(POWER_DIR, exist_ok=True)

'''params_2025_milwaukee = {
    "start": start_2025,
    "end": end_2025,
    "latitude": 43.04,
    "longitude": -87.90,
    "community": "ag",
    "parameters": "T2M,T2MDEW,RH2M",
    "time-standard": "utc"

    testing out how to call nasa power


}
response_2025 = requests.get(
    f"{NASA_POWER_API_URL}/hourly/point",
    params = params_2025_milwaukee
)'''


for i in range(len(cities)):
    
        for j in range(len(summers)):
            city_name = cities[i]["name"]
            file_name = f"power_{city_name}_{summers[j]["year"]}.json"
            final_file_path = os.path.join(POWER_DIR, file_name)
            if os.path.exists(final_file_path):
                    print(f"File '{final_file_path}' already exists. Skipping download.")
            else:
                params = {
                    "start": summers[j]["start"],
                    "end": summers[j]["end"],
                    "latitude": cities[i]["lat"],
                    "longitude": cities[i]["lon"],
                    "community": "ag",
                    "parameters": "T2M,T2MDEW,RH2M",
                    "time-standard": "utc"
                }
                response = requests.get(
                    f"{NASA_POWER_API_URL}/hourly/point",
                    params=params
                )
                response.raise_for_status()

                data = response.json()
            

                
                with open(final_file_path, "w", encoding="utf-8") as file:
                    json.dump(data, file, indent = 4)
                time.sleep(2)
            


        

    