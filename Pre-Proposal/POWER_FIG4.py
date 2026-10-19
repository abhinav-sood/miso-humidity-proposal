import geopandas as gpd
import matplotlib.pyplot as plt
from matplotlib.colors import Normalize
from shapely.geometry import box
import numpy as np
from shapely.geometry import Point
import pandas as pd

metros_upper_midwest = [
    {"city": "Chicago, IL", "lat": 41.8781, "lon": -87.6298, "pop": 9500000},
    {"city": "Twin Cities, MN", "lat": 44.9778, "lon": -93.2650, "pop": 3700000},
    {"city": "Detroit, MI", "lat": 42.3314, "lon": -83.0458, "pop": 4300000},
    {"city": "Indianapolis, IN", "lat": 39.7684, "lon": -86.1581, "pop": 2100000},
    {"city": "Milwaukee, WI", "lat": 43.0389, "lon": -87.9065, "pop": 1570000},
    {"city": "Grand Rapids, MI", "lat": 42.9634, "lon": -85.6681, "pop": 1090000},
    {"city": "Des Moines, IA", "lat": 41.6005, "lon": -93.6091, "pop": 730000},
    {"city": "Madison, WI", "lat": 43.0731, "lon": -89.4012, "pop": 680000},
    {"city": "Peoria, IL", "lat": 40.6936, "lon": -89.5890, "pop": 400000},
    {"city": "Cedar Rapids, IA", "lat": 41.9779, "lon": -91.6656, "pop": 275000},
    {"city": "Duluth, MN", "lat": 46.7867, "lon": -92.1005, "pop": 290000},
    {"city": "Rochester, MN", "lat": 44.0121, "lon": -92.4802, "pop": 225000},
    {"city": "Fort Wayne, IN", "lat": 41.0793, "lon": -85.1394, "pop": 420000},
    {"city": "Evansville, IN", "lat": 37.9716, "lon": -87.5711, "pop": 315000},
    {"city": "Springfield, IL", "lat": 39.7817, "lon": -89.6501, "pop": 208000},
    {"city": "Traverse City, MI", "lat": 44.7631, "lon": -85.6206, "pop": 150000},
]

df_metros = pd.DataFrame(metros_upper_midwest)


url = "https://raw.githubusercontent.com/PublicaMundi/MappingAPI/master/data/geojson/us-states.json"
print("Fetching state boundaries...")
states_gdf = gpd.read_file(url)
miso_states = ["Minnesota", "Wisconsin", "Iowa", "Illinois", "Indiana", "Michigan"]#upper miso
boundary_gdf = states_gdf[states_gdf["name"].isin(miso_states)].copy()
boundary_gdf = boundary_gdf.to_crs(epsg=4326)
print("Boundaries loaded successfully.")


#generate the NASA POWER Grid Mesh
min_lon, min_lat, max_lon, max_lat = boundary_gdf.total_bounds

d_lat = 0.5    
d_lon = 0.625

lats = np.arange(min_lat, max_lat + d_lat, d_lat)
lons = np.arange(min_lon, max_lon + d_lon, d_lon)

grid_polygons = []
for lat in lats:
    for lon in lons:
        cell = box(lon, lat, lon + d_lon, lat + d_lat)
        grid_polygons.append(cell)

grid_gdf = gpd.GeoDataFrame(geometry=grid_polygons, crs="EPSG:4326")
print(f"Generated {len(grid_gdf)} NASA POWER grid cells across the bounding box.")

grid_clipped = grid_gdf[grid_gdf.intersects(boundary_gdf.union_all('unary'))].copy()

print(f"Retained {len(grid_clipped)} NASA grid cells intersecting the footprint.")



#population centers
points_gdf = gpd.GeoDataFrame(
    df_metros,
    geometry=gpd.points_from_xy(df_metros["lon"], df_metros["lat"]),
    crs="EPSG:4326",
)


grid_clipped = grid_clipped.reset_index(drop=True)
grid_clipped["cell_id"] = grid_clipped.index

joined = gpd.sjoin(points_gdf, grid_clipped, how="inner", predicate="within")
pop_per_cell = joined.groupby("cell_id")["pop"].sum().to_dict()

grid_clipped["population"] = grid_clipped["cell_id"].map(pop_per_cell).fillna(0)
total_pop = grid_clipped["population"].sum()
grid_clipped["pop_weight_pct"] = (grid_clipped["population"] / total_pop) * 100

fig, ax = plt.subplots(figsize=(10, 10), facecolor="#F8FAFC")
ax.set_facecolor("#EDF2F7")

# 1. Base footprint fill
boundary_gdf.plot(
    ax=ax,
    facecolor="#F1F5F9",
    edgecolor="none",
    zorder=1
)

# 2. NASA Grid Choropleth
norm = Normalize(vmin=0, vmax=max(grid_clipped["pop_weight_pct"].max(), 35))
grid_clipped.plot(
    ax=ax,
    column="pop_weight_pct",
    cmap="YlOrRd",
    norm=norm,
    edgecolor="#94A3B8",
    linewidth=0.5,
    linestyle=":",
    alpha=0.85,
    legend=True,
    legend_kwds={
        "label": "Population Weight (% of Regional Total)",
        "shrink": 0.72,
        "pad": 0.03,
        "format": "%.0f%%"
    },
    zorder=2
)

# 3. State & Footprint Boundaries
boundary_gdf.boundary.plot(
    ax=ax,
    color="#0F172A",
    linewidth=1.2,
    zorder=3
)

# 4. Demand Center Points
points_gdf.plot(
    ax=ax,
    color="#1E3A8A",
    markersize=points_gdf["pop"] / 28000,
    alpha=0.75,
    edgecolor="#FFFFFF",
    linewidth=1.1,
    zorder=4
)

# 5. Clean Label Badges with Offsets
label_offsets = {
    "Chicago, IL": (10, -14),
    "Twin Cities, MN": (10, 8),
    "Detroit, MI": (10, 6),
    "Indianapolis, IN": (10, -6),
    "Milwaukee, WI": (10, 4),
    "Madison, WI": (-55, 10),
}

for _, row in points_gdf.iterrows():
    if row["city"] in label_offsets:
        dx, dy = label_offsets[row["city"]]
        name = row["city"].split(",")[0]
        ax.annotate(
            name,
            xy=(row["lon"], row["lat"]),
            xytext=(dx, dy),
            textcoords="offset points",
            fontsize=8.5,
            fontweight="semibold",
            color="#0F172A",
            bbox=dict(boxstyle="round,pad=0.2", facecolor="#FFFFFF", edgecolor="#CBD5E1", alpha=0.9, lw=0.6),
            arrowprops=dict(arrowstyle="-", color="#64748B", lw=0.6),
            zorder=5
        )

# 6. Framing, Margins & Annotations
bounds = boundary_gdf.total_bounds
ax.set_xlim(bounds[0] - 0.8, bounds[2] + 0.8)
ax.set_ylim(bounds[1] - 0.6, bounds[3] + 0.6)

ax.set_title(
    "Spatial Mismatch: NASA POWER Grid Resolution vs. Electricity Demand Centers",
    fontsize=12,
    fontweight="bold",
    color="#0F172A",
    pad=14
)
ax.set_xlabel("Longitude (°W)", fontsize=9, color="#475569", labelpad=6)
ax.set_ylabel("Latitude (°N)", fontsize=9, color="#475569", labelpad=6)
ax.tick_params(colors="#475569", labelsize=8.5)
for spine in ax.spines.values():
    spine.set_edgecolor("#CBD5E1")

# Methodological takeaway note
ax.text(
    0.02, 0.03,
    "NASA POWER: 0.5° × 0.625° regular cells\nCircles: Population-weighted cooling/heating demand clusters",
    transform=ax.transAxes,
    fontsize=8,
    color="#475569",
    bbox=dict(boxstyle="square,pad=0.4", facecolor="#FFFFFF", edgecolor="#E2E8F0", alpha=0.95),
    zorder=6
)

plt.savefig("figure4_spatial_mismatch_clean.png", dpi=300, bbox_inches="tight")
print("Saved publication-ready map to figure4_spatial_mismatch_clean.png")