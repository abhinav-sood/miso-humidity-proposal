import requests
from pathlib import Path


NASA_POWER_API_URL = "https://power.larc.nasa.gov/api/temporal"
start_2025 = 20250529
end_2025 = 20250902
start_2026 = 20260529
end_2026 = 20260902

cities = ["Minneapolis", "Detroit", "St. Louis", "Des Moines", "Indianapolis", "New Orleans", "Little Rock", "Milwaukee"]
cities_latitude = [44.59, 42.33, 38.63, 41.59, 39.77, 29.97, 34.74, 43.03]
cities_longitude = [-93.27, -83.05, -90.20, 93.61, -86.16, -90.08, -92.29, -97.90]

PROJECT_ROOT = Path(__file__).resolve().parent.parent
POWER_DIR = PROJECT_ROOT / "data" / "raw" / "nasa_power"

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

for i in len(cities):
   params_2025 = {
        "start": start_2025,
        "end": end_2025,
        "latitude": cities_latitude[i],
        "longitude": cities_longitude[i],
        "community": "ag",
        "parameters": "T2M,T2MDEW,RH2M",
        "time-standard": "utc"
    }
   