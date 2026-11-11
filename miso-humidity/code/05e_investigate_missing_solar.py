import json
from pathlib import Path


path = Path("../data/raw/nasa_power_v2/power_madison_2026.json")
with open(path, encoding="utf-8") as f:
    data = json.load(f)

solar = data["properties"]["parameter"]["ALLSKY_SFC_SW_DWN"]
missing = [t for t, v in solar.items() if v == -999]

print(len(missing))
print(missing[0], missing[-1])