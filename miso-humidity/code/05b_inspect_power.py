import json
from pathlib import Path

import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parent.parent
POWER_DIR = PROJECT_ROOT / "data" / "raw" / "nasa_power"


requested = {
    "minneapolis": (44.98, -93.27), "madison": (43.07, -89.40),
    "detroit": (42.33, -83.05),     "st_louis": (38.63, -90.20),
    "des_moines": (41.59, -93.62),  "indianapolis": (39.77, -86.16),
    "new_orleans": (29.95, -90.07), "little_rock": (34.75, -92.29),
}
MISSING_CODE = -999   

rows = []
for path in sorted(POWER_DIR.glob("power_*.json")):
    city, year = path.stem.replace("power_", "").rsplit("_", 1)
    with open(path, encoding="utf-8") as f:
        data = json.load(f)

    lon, lat, elev = data["geometry"]["coordinates"]
    req_lat, req_lon = requested[city]
    params = data["properties"]["parameter"]

    row = {
        "city": city, "year": year,
        "lat_diff": round(lat - req_lat, 3), "lon_diff": round(lon - req_lon, 3),
    }

    for p in ["T2M", "T2MDEW", "RH2M"]:
        s = pd.Series(params[p])
        row[f"{p}_n"] = len(s)
        row[f"{p}_missing"] = int((s == MISSING_CODE).sum())
        good = s[s != MISSING_CODE]
        row[f"{p}_min"] = good.min()
        row[f"{p}_max"] = good.max()
        if p == "T2M":
            row["first"] = s.index.min()
            row["last"] = s.index.max()
            
            hours = good.index.str[-2:].astype(int)
            row["warmest_utc_hour"] = int(good.groupby(hours.values).mean().idxmax())
    rows.append(row)

out = pd.DataFrame(rows)
pd.set_option("display.width", 250)
pd.set_option("display.max_columns", None)
print(out.to_string(index=False))