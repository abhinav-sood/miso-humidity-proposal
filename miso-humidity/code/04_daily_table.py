"""
04_daily_table.py

Builds the daily table (one row per US Central day, June 1 - Aug 31) and the first
2025-vs-2026 comparison figures.

Reads:   data/processed/hourly_load_filled_utc_{2025,2026}.csv   (from 03_fill_from_miso.py)
Writes:  data/processed/daily_load_{2025,2026}.csv, data/processed/daily_load_all.csv
         outputs/tables/summer_comparison.csv
         outputs/figures/daily_peak_2025_vs_2026.png
         outputs/figures/hourly_profile_2025_vs_2026.png

Definitions (see LOG.md):
  * A "day" is a US Central (America/Chicago) calendar day. June-August has no clock changes,
    so every day has exactly 24 hours (checked below).
  * peak_mw      = highest HOURLY MEAN load in the day (not the highest 5-minute reading).
  * hour_of_peak = local hour (0-23) in which that highest hourly mean occurs.
  * total_mwh    = sum of the 24 hourly means. Only computed for complete days.
  * usable       = all 24 hours present. Days with any missing hour are kept in the table
                   but flagged usable = False, so the exclusion is visible and reversible.

The comparison numbers below are NOT adjusted for weather. They describe the two summers;
they do not explain the difference. Weather comes in a later step.
"""

import sys
from pathlib import Path

import matplotlib
matplotlib.use("Agg")  # draw to files, no window needed
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parent.parent
PROC_DIR = PROJECT_ROOT / "data" / "processed"
FIG_DIR = PROJECT_ROOT / "outputs" / "figures"
TABLE_DIR = PROJECT_ROOT / "outputs" / "tables"
FIG_DIR.mkdir(parents=True, exist_ok=True)
TABLE_DIR.mkdir(parents=True, exist_ok=True)

YEARS = [2025, 2026]
LOCAL_TZ = "America/Chicago"

# --------------------------------------------------------------------------------------
# Hourly (UTC) -> hourly (Central), trimmed to June 1 - Aug 31 local
# --------------------------------------------------------------------------------------
hourly_local = {}
for year in YEARS:
    path = PROC_DIR / f"hourly_load_filled_utc_{year}.csv"
    if not path.exists():
        sys.exit(f"Missing {path}. Run 03_fill_from_miso.py first.")
    df = pd.read_csv(path, index_col="hour_utc", parse_dates=["hour_utc"])
    df.index = df.index.tz_convert("UTC").tz_convert(LOCAL_TZ)

    start = pd.Timestamp(f"{year}-06-01", tz=LOCAL_TZ)
    end = pd.Timestamp(f"{year}-09-01", tz=LOCAL_TZ)          # exclusive
    df = df[(df.index >= start) & (df.index < end)].copy()

    # checks: 92 days x 24 hours, no daylight saving changes, no duplicate hours
    assert len(df) == 92 * 24, f"{year}: expected {92 * 24} hours in the window, found {len(df)}"
    assert not df.index.duplicated().any(), f"{year}: duplicate local hours"
    assert str(df.index[0]) .startswith(f"{year}-06-01 00:00:00-05:00"), f"{year}: window start is off: {df.index[0]}"
    assert str(df.index[-1]).startswith(f"{year}-08-31 23:00:00-05:00"), f"{year}: window end is off: {df.index[-1]}"
    df["day"] = df.index.normalize()
    hourly_local[year] = df
    print(f"{year}: {len(df)} local hours, first {df.index[0]}, last {df.index[-1]}, "
          f"missing {int(df['load_filled'].isna().sum())}")


# --------------------------------------------------------------------------------------
# Daily table
# --------------------------------------------------------------------------------------
def peak_hour(s: pd.Series):
    return s.idxmax().hour if s.notna().any() else np.nan


daily_tables = []
for year, df in hourly_local.items():
    g = df.groupby("day")
    daily = pd.DataFrame({
        "n_valid_hours": g["load_filled"].count(),
        "n_hours_from_miso": g["source"].apply(lambda s: int((s == "miso_dfal").sum())),
        "peak_mw": g["load_filled"].max(),
        "hour_of_peak": g["load_filled"].apply(peak_hour),
        "mean_mw": g["load_filled"].mean(),
        "min_mw": g["load_filled"].min(),
        "total_mwh": g["load_filled"].sum(min_count=24),
    })
    daily["usable"] = daily["n_valid_hours"] == 24
    daily["year"] = year
    daily["day_of_week"] = daily.index.dayofweek      # Monday = 0
    daily["is_weekend"] = daily["day_of_week"] >= 5
    daily.index = daily.index.tz_localize(None)       # plain calendar dates from here on
    daily.index.name = "local_day"

    n_days = len(daily)
    n_ok = int(daily["usable"].sum())
    print(f"\n{year}: {n_days} days, {n_ok} usable (all 24 hours present), {n_days - n_ok} flagged")
    if n_days - n_ok:
        bad = daily.loc[~daily["usable"], "n_valid_hours"]
        print("  flagged days (date: valid hours):")
        for d, n in bad.items():
            print(f"    {d.date()}: {n}")
    print(f"  days that include hours filled from MISO: {int((daily['n_hours_from_miso'] > 0).sum())}")

    daily.to_csv(PROC_DIR / f"daily_load_{year}.csv")
    daily_tables.append(daily)

daily_all = pd.concat(daily_tables)
daily_all.to_csv(PROC_DIR / "daily_load_all.csv")

# --------------------------------------------------------------------------------------
# Unadjusted comparison of the two summers (usable days only)
# --------------------------------------------------------------------------------------
use = daily_all[daily_all["usable"]]
rows = []
for label, sub in [("all days", use), ("weekdays", use[~use["is_weekend"]]), ("weekends", use[use["is_weekend"]])]:
    a = sub[sub["year"] == YEARS[0]]
    b = sub[sub["year"] == YEARS[1]]
    for col in ["peak_mw", "mean_mw", "min_mw"]:
        rows.append({
            "days": label, "measure": col,
            f"{YEARS[0]}_mean": a[col].mean(), f"{YEARS[1]}_mean": b[col].mean(),
            "pct_difference": (b[col].mean() / a[col].mean() - 1) * 100,
            f"{YEARS[0]}_n_days": len(a), f"{YEARS[1]}_n_days": len(b),
        })
comp = pd.DataFrame(rows).round(2)
comp.to_csv(TABLE_DIR / "summer_comparison.csv", index=False)
print("\nUnadjusted summer comparison (NOT controlled for weather):")
print(comp.to_string(index=False))

# --------------------------------------------------------------------------------------
# Figures. Palette: blue = first summer, orange = second summer (validated default palette).
# --------------------------------------------------------------------------------------
SURFACE, INK, INK2, GRID = "#fcfcfb", "#0b0b0b", "#52514e", "#e6e5e1"
COLORS = {2025: "#2a78d6", 2026: "#eb6834"}


def style(ax):
    ax.set_facecolor(SURFACE)
    for side in ("top", "right"):
        ax.spines[side].set_visible(False)
    for side in ("left", "bottom"):
        ax.spines[side].set_color(GRID)
    ax.tick_params(colors=INK2, labelsize=9)
    ax.grid(axis="y", color=GRID, linewidth=0.8)
    ax.set_axisbelow(True)


# Figure 1: daily peak through the summer, both years on the same calendar axis
fig, ax = plt.subplots(figsize=(9, 4.6), facecolor=SURFACE)
style(ax)
for year in YEARS:
    d = daily_all[(daily_all["year"] == year) & daily_all["usable"]]
    # put both years on a common date axis (use a dummy non-leap year)
    x = pd.to_datetime(d.index.strftime("2001-%m-%d"))
    ax.plot(x, d["peak_mw"] / 1000, color=COLORS[year], linewidth=2, label=str(year))
    ax.text(x[-1] + pd.Timedelta(days=1), d["peak_mw"].iloc[-1] / 1000, f" {year}",
            color=INK, va="center", fontsize=10)
ax.set_ylabel("Daily peak (GW, highest hourly mean)", color=INK2, fontsize=10)
ax.set_title("MISO daily peak load, June-August (usable days only)", color=INK, fontsize=12, loc="left")
ax.xaxis.set_major_formatter(matplotlib.dates.DateFormatter("%b %d"))
ax.set_xlim(pd.Timestamp("2001-05-31"), pd.Timestamp("2001-09-06"))
ax.legend(frameon=False, labelcolor=INK2, fontsize=9, loc="upper left")
fig.tight_layout()
fig.savefig(FIG_DIR / "daily_peak_2025_vs_2026.png", dpi=160, facecolor=SURFACE)
plt.close(fig)

# Figure 2: average load by local hour of day, weekdays vs weekends
fig, axes = plt.subplots(1, 2, figsize=(10, 4.4), facecolor=SURFACE, sharey=True)
for ax, (title, weekend) in zip(axes, [("Weekdays", False), ("Weekends", True)]):
    style(ax)
    for year in YEARS:
        df = hourly_local[year]
        ok_days = daily_all[(daily_all["year"] == year) & daily_all["usable"] & (daily_all["is_weekend"] == weekend)].index
        sel = df[df["day"].dt.tz_localize(None).isin(ok_days)]
        prof = sel.groupby(sel.index.hour)["load_filled"].mean() / 1000
        ax.plot(prof.index, prof.values, color=COLORS[year], linewidth=2, label=str(year))
        ax.text(23.3, prof.values[-1], f" {year}", color=INK, va="center", fontsize=9)
    ax.set_title(title, color=INK, fontsize=11, loc="left")
    ax.set_xlabel("Local hour of day (Central)", color=INK2, fontsize=10)
    ax.set_xticks(range(0, 24, 3))
    ax.set_xlim(0, 25)
axes[0].set_ylabel("Mean load (GW)", color=INK2, fontsize=10)
handles, labels = axes[0].get_legend_handles_labels()
fig.legend(handles, labels, frameon=False, labelcolor=INK2, fontsize=9, loc="upper right", ncol=2)
fig.tight_layout(rect=[0, 0, 1, 0.94])   # leave room for the legend above the panels
fig.savefig(FIG_DIR / "hourly_profile_2025_vs_2026.png", dpi=160, facecolor=SURFACE)
plt.close(fig)

print("\nSaved daily tables, summer_comparison.csv, and two figures.")