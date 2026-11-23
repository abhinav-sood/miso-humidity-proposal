"""
11_report.py

Makes the figures and a plain-language results summary (RESULTS.md) from the saved tables.

Reads:   outputs/tables/model_comparison.csv, humidity_effect.csv, vs_miso.csv, predictions_daily.csv,
         walk_forward_predictions.csv (if present), best_params.csv, feature_notes.csv
Writes:  outputs/figures/fig_model_comparison.png
         outputs/figures/fig_humidity_effect.png
         outputs/figures/fig_pred_vs_actual_2026.png
         outputs/figures/fig_timeseries_2026.png
         outputs/RESULTS.md

Nothing here fits or selects anything. The models and the comparisons shown were fixed in advance in
10_models.py; this script only reports them. The sentences in RESULTS.md are generated from the numbers,
so if you change the data and rerun, the text follows.
"""

import datetime
import sys
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parent.parent
TABLE_DIR = PROJECT_ROOT / "outputs" / "tables"
FIG_DIR = PROJECT_ROOT / "outputs" / "figures"
OUT_DIR = PROJECT_ROOT / "outputs"
FIG_DIR.mkdir(parents=True, exist_ok=True)

for name in ["model_comparison.csv", "humidity_effect.csv", "vs_miso.csv", "predictions_daily.csv"]:
    if not (TABLE_DIR / name).exists():
        sys.exit(f"Missing outputs/tables/{name}. Run 10_models.py first.")

mc = pd.read_csv(TABLE_DIR / "model_comparison.csv")
he = pd.read_csv(TABLE_DIR / "humidity_effect.csv")
vm = pd.read_csv(TABLE_DIR / "vs_miso.csv")
pred = pd.read_csv(TABLE_DIR / "predictions_daily.csv", index_col="local_day", parse_dates=["local_day"])
HAS_WF = "wf_rmse" in mc.columns and mc["wf_rmse"].notna().any()

# --------------------------------------------------------------------------------------
# Names and colours
# --------------------------------------------------------------------------------------
NICE = {
    "R1_regression_temp": "Regression: temperature",
    "R2_regression_humidity": "Regression: + humidity",
    "RF_E1_temp": "Random forest: temperature",
    "RF_E2_humidity": "Random forest: + humidity",
    "RF_E3_expanded": "Random forest: + sun, wind, rain",
    "RF_E4_engineered": "Random forest: + heat-wave features",
    "GBM_E1_temp": "Gradient boosting: temperature",
    "GBM_E2_humidity": "Gradient boosting: + humidity",
    "GBM_E3_expanded": "Gradient boosting: + sun, wind, rain",
    "GBM_E4_engineered": "Gradient boosting: + heat-wave features",
    "MISO_day_ahead_forecast": "MISO day-ahead forecast",
}
TIMING_NICE = {"same_day": "same-day weather (upper bound)", "day_before": "day-before weather (forecast)"}
FAMILY_COLOR = {"REG": "#2a78d6", "RF": "#1f9d8b", "GBM": "#7a5cc7", "MISO": "#eb6834"}
SURFACE, INK, INK2, GRID = "#fcfcfb", "#0b0b0b", "#52514e", "#e6e5e1"
ORDER = list(NICE)[:-1]


def style(ax, grid_axis="y"):
    ax.set_facecolor(SURFACE)
    for side in ("top", "right"):
        ax.spines[side].set_visible(False)
    for side in ("left", "bottom"):
        ax.spines[side].set_color(GRID)
    ax.tick_params(colors=INK2, labelsize=9)
    ax.grid(axis=grid_axis, color=GRID, linewidth=0.8)
    ax.set_axisbelow(True)


def gw(x, signed=False):
    return f"{x / 1000:+.2f}" if signed else f"{x / 1000:.2f}"


miso = mc[mc["model"] == "MISO_day_ahead_forecast"].iloc[0]
n_test = int(miso["n_test"])
n_train = int(miso["n_train"])

# --------------------------------------------------------------------------------------
# Figure 1: out-of-sample error of every model, with MISO's error as a line
# --------------------------------------------------------------------------------------
fig, axes = plt.subplots(1, 2, figsize=(12, 5.6), facecolor=SURFACE, sharex=True)
xmax = max(mc["test_rmse"].max(), miso["test_rmse"]) / 1000 * 1.18
for ax, timing in zip(axes, ["day_before", "same_day"]):
    style(ax, "x")
    sub = mc[mc["timing"] == timing].set_index("model").loc[ORDER]
    y = np.arange(len(sub))
    ax.barh(y, sub["test_rmse"] / 1000, color=[FAMILY_COLOR[f] for f in sub["family"]], height=0.66)
    for yi, v in zip(y, sub["test_rmse"] / 1000):
        ax.text(v + xmax * 0.008, yi, f"{v:.2f}", va="center", fontsize=8.5, color=INK2)
    ax.axvline(miso["test_rmse"] / 1000, color=FAMILY_COLOR["MISO"], linestyle="--", linewidth=1.8,
               label=f"MISO day-ahead forecast ({miso['test_rmse'] / 1000:.2f})")
    ax.legend(loc="upper center", bbox_to_anchor=(0.5, -0.12), frameon=False, fontsize=9, labelcolor=FAMILY_COLOR["MISO"])
    ax.set_yticks(y)
    ax.set_yticklabels([NICE[m] for m in sub.index], fontsize=9, color=INK)
    ax.invert_yaxis()
    ax.set_xlim(0, xmax)
    ax.set_title(f"Using the {TIMING_NICE[timing]}", loc="left", color=INK, fontsize=11)
    ax.set_xlabel("RMSE on 2026 daily peaks (GW)  -  lower is better", color=INK2, fontsize=9.5)
fig.suptitle(f"How far off each model is on summer 2026 (trained on 2025, {n_test} test days)", x=0.01, ha="left",
             color=INK, fontsize=12.5)
fig.tight_layout(rect=[0, 0, 1, 0.95])
fig.savefig(FIG_DIR / "fig_model_comparison.png", dpi=160, facecolor=SURFACE)
plt.close(fig)

# --------------------------------------------------------------------------------------
# Figure 2: effect of adding humidity (change in RMSE with 95% interval)
# --------------------------------------------------------------------------------------
hum = he[he["added"] == "humidity"].copy()
hum = hum.assign(_o=hum["timing"].map({"day_before": 0, "same_day": 1})).sort_values("_o", kind="stable").drop(columns="_o")
hum["label"] = hum["model_family"] + ", " + hum["timing"].map(TIMING_NICE) + ", " + hum["evaluation"].str.split(" \\(").str[0]
hum = hum.iloc[::-1].reset_index(drop=True)
fig, ax = plt.subplots(figsize=(10, 0.55 * len(hum) + 1.8), facecolor=SURFACE)
style(ax, "x")
y = np.arange(len(hum))
for yi, r in zip(y, hum.itertuples()):
    color = "#1f9d8b" if r.ci_high_mw < 0 else ("#c0392b" if r.ci_low_mw > 0 else INK2)
    ax.plot([r.ci_low_mw / 1000, r.ci_high_mw / 1000], [yi, yi], color=color, linewidth=2.2)
    ax.plot(r.delta_mw / 1000, yi, "o", color=color, markersize=7)
ax.axvline(0, color=INK, linewidth=1)
ax.set_yticks(y)
ax.set_yticklabels(hum["label"], fontsize=8.5, color=INK)
ax.set_xlabel("Change in RMSE when humidity is added (GW)   <- humidity helps | humidity hurts ->", color=INK2, fontsize=9.5)
ax.set_title("Does adding humidity improve the prediction?\n(dots = change, lines = 95% interval)", loc="left", color=INK, fontsize=11.5)
fig.tight_layout()
fig.savefig(FIG_DIR / "fig_humidity_effect.png", dpi=160, facecolor=SURFACE)
plt.close(fig)

# --------------------------------------------------------------------------------------
# Figure 3: predicted vs actual on the 2026 test days
# --------------------------------------------------------------------------------------
test_days = pred[pred["year"] == 2026].dropna(subset=["actual_mw"])
test_days = test_days.dropna(subset=["same_day__R1_regression_temp"])
panels = [("MISO day-ahead forecast", "miso_forecast_mw", "MISO"),
          ("Regression + humidity", "R2_regression_humidity", "REG"),
          ("Gradient boosting, temperature only", "GBM_E1_temp", "GBM"),
          ("Gradient boosting + humidity", "GBM_E2_humidity", "GBM")]
fig, axes = plt.subplots(2, 4, figsize=(15, 7.4), facecolor=SURFACE, sharex=True, sharey=True)
lo_v = min(test_days["actual_mw"].min(), 1e9) / 1000 - 4
hi_v = test_days["actual_mw"].max() / 1000 + 4
for r_i, timing in enumerate(["day_before", "same_day"]):
    for c_i, (title, col, fam) in enumerate(panels):
        ax = axes[r_i, c_i]
        style(ax, "both")
        series = test_days[col] if col == "miso_forecast_mw" else test_days[f"{timing}__{col}"]
        ax.scatter(test_days["actual_mw"] / 1000, series / 1000, s=16, alpha=0.8, color=FAMILY_COLOR[fam])
        ax.plot([lo_v, hi_v], [lo_v, hi_v], color=INK2, linewidth=1, linestyle=":")
        rmse = np.sqrt(np.mean((series - test_days["actual_mw"]) ** 2)) / 1000
        ax.set_title(f"{title}\nRMSE {rmse:.2f} GW", loc="left", fontsize=9.5, color=INK)
        ax.set_xlim(lo_v, hi_v)
        ax.set_ylim(lo_v, hi_v)
        if c_i == 0:
            ax.set_ylabel(f"Predicted peak (GW)\n[{TIMING_NICE[timing]}]", color=INK2, fontsize=9)
        if r_i == 1:
            ax.set_xlabel("Actual peak (GW)", color=INK2, fontsize=9)
fig.suptitle("Predicted vs. actual daily peak, summer 2026 (dotted line = perfect). MISO panel is repeated in both rows.",
             x=0.01, ha="left", color=INK, fontsize=12)
fig.tight_layout(rect=[0, 0, 1, 0.95])
fig.savefig(FIG_DIR / "fig_pred_vs_actual_2026.png", dpi=150, facecolor=SURFACE)
plt.close(fig)

# --------------------------------------------------------------------------------------
# Figure 4: the 2026 summer as a time series
# --------------------------------------------------------------------------------------
fig, ax = plt.subplots(figsize=(11, 5), facecolor=SURFACE)
style(ax, "y")
ax.plot(test_days.index, test_days["actual_mw"] / 1000, color=INK, linewidth=2.2, label="Actual")
ax.plot(test_days.index, test_days["miso_forecast_mw"] / 1000, color=FAMILY_COLOR["MISO"], linewidth=1.6, label="MISO forecast")
ax.plot(test_days.index, test_days["same_day__GBM_E2_humidity"] / 1000, color=FAMILY_COLOR["GBM"], linewidth=1.4,
        label="Gradient boosting + humidity (same-day weather)")
ax.plot(test_days.index, test_days["day_before__GBM_E2_humidity"] / 1000, color=FAMILY_COLOR["RF"], linewidth=1.4,
        linestyle="--", label="Gradient boosting + humidity (day-before weather)")
ax.set_ylabel("Daily peak load (GW)", color=INK2, fontsize=10)
ax.set_title("Summer 2026 daily peak: actual vs. MISO's forecast vs. models trained on 2025", loc="left", color=INK, fontsize=11.5)
ax.xaxis.set_major_formatter(matplotlib.dates.DateFormatter("%b %d"))
ax.legend(frameon=False, fontsize=9, labelcolor=INK2, loc="lower center", ncol=2, bbox_to_anchor=(0.5, -0.28))
fig.tight_layout()
fig.savefig(FIG_DIR / "fig_timeseries_2026.png", dpi=160, facecolor=SURFACE)
plt.close(fig)

# --------------------------------------------------------------------------------------
# RESULTS.md
# --------------------------------------------------------------------------------------
def row(timing, model):
    return mc[(mc["timing"] == timing) & (mc["model"] == model)].iloc[0]


def effect_sentence(r):
    return (f"{r.model_family}, {TIMING_NICE[r.timing]}: RMSE {gw(r.rmse_without_mw)} GW without {r.added}, "
            f"{gw(r.rmse_with_mw)} GW with ({gw(r.delta_mw, True)} GW, {r.delta_pct:+.1f}%; 95% interval "
            f"{gw(r.ci_low_mw, True)} to {gw(r.ci_high_mw, True)} GW): {r.verdict}.")


fixed = "fixed split (train 2025, test 2026)"
hum_fixed = he[(he["added"] == "humidity") & (he["evaluation"] == fixed)]
hum_wf = he[(he["added"] == "humidity") & (he["evaluation"] == "walk-forward")]
extra = he[(he["added"] != "humidity") & (he["evaluation"] == fixed) & (he["model_family"] == "Gradient boosting")]

gbm_sd = hum_fixed[(hum_fixed["model_family"] == "Gradient boosting") & (hum_fixed["timing"] == "same_day")].iloc[0]
gbm_db = hum_fixed[(hum_fixed["model_family"] == "Gradient boosting") & (hum_fixed["timing"] == "day_before")].iloc[0]

key_models = ["R1_regression_temp", "R2_regression_humidity", "GBM_E1_temp", "GBM_E2_humidity",
              "GBM_E3_expanded", "GBM_E4_engineered", "RF_E2_humidity"]
lines = []
add = lines.append
add("# Preliminary results: how close can NASA POWER weather get to MISO's daily peak load forecast?")
add("")
add(f"*Generated automatically by `11_report.py` on {datetime.date.today().isoformat()}. Exploratory, two summers, "
    f"{n_test} test days. Numbers are for the models exactly as specified in `10_models.py`; nothing was tuned on 2026.*")
add("")
add("## 1. The short version")
add("")
add(f"- **Question:** how close can a model built only on free NASA POWER weather get to MISO's own day-ahead forecast of "
    f"daily peak summer load, and does adding humidity help?")
add(f"- **Method:** models fitted on summer 2025 ({n_train} days) and tested once on summer 2026 ({n_test} days).")
add(f"- **MISO's forecast** was off by {gw(miso['test_rmse'])} GW (RMSE; {miso['test_mape']:.2f}% on average) on those days.")
r1sd, g2sd = row("same_day", "R2_regression_humidity"), row("same_day", "GBM_E2_humidity")
r1db, g2db = row("day_before", "R2_regression_humidity"), row("day_before", "GBM_E2_humidity")
r0db = row("day_before", "R1_regression_temp")
reg_db = hum_fixed[(hum_fixed["model_family"] == "Regression") & (hum_fixed["timing"] == "day_before")].iloc[0]
reg_sd = hum_fixed[(hum_fixed["model_family"] == "Regression") & (hum_fixed["timing"] == "same_day")].iloc[0]
add(f"- **Main result, a real forecast (only the previous day's weather is used):** the regression was off by {gw(r0db['test_rmse'])} GW with "
    f"temperature only and {gw(r1db['test_rmse'])} GW with humidity added; gradient boosting with humidity was off by {gw(g2db['test_rmse'])} GW. "
    f"MISO is off by {gw(miso['test_rmse'])} GW, but it has a real weather forecast for the target day and we only have yesterday's weather (see section 6.1).")
add(f"- **Does humidity help in the forecast setting?** {effect_sentence(reg_db)} {effect_sentence(gbm_db)}")
add(f"- **Upper bound (the weather that actually happened on the target day, which no forecaster has a day ahead):** regression with humidity "
    f"{gw(r1sd['test_rmse'])} GW ({r1sd['test_mape']:.2f}%), gradient boosting with humidity {gw(g2sd['test_rmse'])} GW ({g2sd['test_mape']:.2f}%). "
    f"This shows what perfectly known weather could support. Humidity effect here: {effect_sentence(reg_sd)} {effect_sentence(gbm_sd)}")
add("- **Read this as preliminary:** two summers, about 90 test days, and a 2025-to-2026 level shift all limit what can be concluded (section 6).")
add("")
add("## 2. What was done")
add("")
add("- **Load:** Grid Status `miso_load` (5-minute) averaged to hourly, gaps filled from MISO's own reports after a validation "
    "(median difference 0.3%). *Daily peak* = the highest hourly average in a US Central day, June 1 to Aug 31.")
add("- **Weather:** NASA POWER hourly data (MERRA-2 reanalysis, requested in UTC) at 8 points across the MISO footprint "
    "(Minneapolis, Madison, Detroit, St. Louis, Des Moines, Indianapolis, New Orleans, Little Rock), averaged into one "
    "MISO-wide series. Variables: temperature (daily high), specific humidity, sunlight, wind, rain.")
add("- **Humidity variable:** specific humidity (`QV2M`) rather than dew point. Dr. Holloway advised avoiding dew point because "
    "of known problems with MERRA-2 dew point; the data also showed hours with dew point above air temperature.")
add("- **MISO benchmark:** Grid Status `miso_load_forecast_mid_term_by_region`. MISO publishes a new forecast every day; for every "
    "hour I used the newest version (published 24-47 hours earlier), summed the 10 zones, and took each day's highest hour.")
add("- **Models:** (1) ordinary regression: temperature and temperature squared with day-of-week and holiday adjustments, "
    "then the same plus humidity; (2) machine learning (gradient boosting, the primary one, and random forest) with four "
    "nested sets of inputs: temperature only; + humidity; + sunlight, wind and rain; + previous-day temperature and heat-wave length.")
add("- **Two weather timings:** *day-before* uses only the previous day's weather: everything is known a day ahead, so this is the "
    "forecast setting and the main result. *Same-day* uses the weather of the day being predicted, which no forecaster has a day ahead; "
    "it is reported only as an upper bound on what perfectly known weather could support.")
add("- **Scoring:** RMSE (typical error in GW; large misses count more), MAPE (average % error), R-squared, and bias (average "
    "prediction minus actual). Uncertainty on differences uses a block bootstrap (7-day blocks) because neighbouring days are related.")
add("- **Two tests:** a *fixed split* (fit on 2025, predict 2026) and a *walk-forward* test (each 2026 day predicted from 2025 plus the "
    "2026 days at least 2 days older), which lets models adapt to the 2026 load level.")
add("")
add("## 3. Results on summer 2026")
add("")
add("| Model | Weather | RMSE (GW) | MAPE (%) | R-squared | Bias (GW) | Walk-forward RMSE (GW) |")
add("|---|---|---|---|---|---|---|")
for timing in ["day_before", "same_day"]:
    for m in key_models:
        r = row(timing, m)
        wf = gw(r["wf_rmse"]) if HAS_WF and pd.notna(r.get("wf_rmse", np.nan)) else "n/a"
        add(f"| {NICE[m]} | {TIMING_NICE[timing]} | {gw(r['test_rmse'])} | {r['test_mape']:.2f} | {r['test_r2']:.3f} | "
            f"{gw(r['test_bias'], True)} | {wf} |")
add(f"| **MISO day-ahead forecast** | (uses a real weather forecast) | **{gw(miso['test_rmse'])}** | **{miso['test_mape']:.2f}** | "
    f"**{miso['test_r2']:.3f}** | **{gw(miso['test_bias'], True)}** | n/a |")
add("")
add("All 20 models are in `outputs/tables/model_comparison.csv` (in-sample numbers included). Figures: "
    "`fig_model_comparison.png`, `fig_pred_vs_actual_2026.png`, `fig_timeseries_2026.png`.")
add("")
add("## 4. Does humidity help?")
add("")
add("Change in RMSE when specific humidity is added (negative = humidity helps). The interval is a 95% block-bootstrap interval; "
    "if it includes zero the data cannot tell the two models apart.")
add("")
add("| Model | Weather | Test | RMSE without (GW) | RMSE with (GW) | Change (GW) | 95% interval (GW) | Verdict |")
add("|---|---|---|---|---|---|---|---|")
for r in pd.concat([hum_fixed, hum_wf]).assign(_o=lambda d: d["timing"].map({"day_before": 0, "same_day": 1})).sort_values(["_o"], kind="stable").itertuples():
    add(f"| {r.model_family} | {TIMING_NICE[r.timing]} | {r.evaluation.split(' (')[0]} | {gw(r.rmse_without_mw)} | {gw(r.rmse_with_mw)} | "
        f"{gw(r.delta_mw, True)} | {gw(r.ci_low_mw, True)} to {gw(r.ci_high_mw, True)} | {r.verdict} |")
add("")
add("Figure: `fig_humidity_effect.png`. Adding sunlight, wind and rain, then heat-wave features, to the gradient boosting model "
    "(fixed split):")
add("")
for r in extra.itertuples():
    add(f"- {effect_sentence(r)} (adds: {r.added})")
add("")
add("## 5. How close to MISO?")
add("")
add("Difference in RMSE between each model and MISO's forecast on the same days (positive = the model is further off than MISO; "
    "95% block-bootstrap interval).")
add("")
add("| Model | Weather | Test | Model RMSE (GW) | MISO RMSE (GW) | Difference (GW) | 95% interval (GW) | Verdict |")
add("|---|---|---|---|---|---|---|---|")
for timing in ["day_before", "same_day"]:
    for m in ["R2_regression_humidity", "GBM_E2_humidity", "GBM_E4_engineered"]:
        for ev in [fixed] + (["walk-forward"] if HAS_WF else []):
            q = vm[(vm["timing"] == timing) & (vm["model"] == m) & (vm["evaluation"] == ev)]
            if q.empty:
                continue
            q = q.iloc[0]
            add(f"| {NICE[m]} | {TIMING_NICE[timing]} | {ev.split(' (')[0]} | {gw(q['rmse_model_mw'])} | {gw(q['rmse_miso_mw'])} | "
                f"{gw(q['delta_mw'], True)} | {gw(q['ci_low_mw'], True)} to {gw(q['ci_high_mw'], True)} | {q['verdict']} |")
add("")
add("## 6. Caveats (please read before quoting any number)")
add("")
add("1. **Observed vs. forecast weather.** NASA POWER describes weather that already happened; it has no forecasts. The *day-before* models "
    "therefore use yesterday's weather as a stand-in for tomorrow's, while MISO's forecast used an actual weather forecast for the target day. "
    "This handicaps our models and probably explains much of the gap to MISO. The *same-day* models are told the true weather, which MISO "
    "did not have, so they flatter the models. What NASA POWER data alone can support lies between the two; only the day-before "
    "numbers are a real forecast.")
add("2. **Level shift between summers.** Daily peaks were about 2.5% higher in 2026 and 2026 was also warmer. A model trained only on 2025 "
    f"carries 2025's level into 2026: the bias column shows the average over- or under-prediction (MISO: {gw(miso['test_bias'], True)} GW). "
    "The walk-forward test shows how much of this goes away when models may learn from earlier 2026 days. This is a description, "
    "not an explanation of the shift.")
b_r1, b_r2 = row("same_day", "R1_regression_temp")["test_bias"], row("same_day", "R2_regression_humidity")["test_bias"]
if abs(b_r2) < abs(b_r1):
    add(f"   In the same-day regression, adding humidity moved the average bias from {gw(b_r1, True)} to {gw(b_r2, True)} GW, so part of its gain "
        "may be humidity absorbing the 2025-to-2026 level shift rather than a pure weather effect. Treat that gain as a lead, not a conclusion.")
add("3. **Hotter days than the training summer.** Tree-based models cannot predict beyond the range they saw in training; if 2026 has "
    "hotter days than 2025, gradient boosting and random forest will under-predict them while the regression can extrapolate.")
add("4. **Small sample.** About 90 days per summer. Differences of a few tenths of a GW between models are within noise; use the intervals.")
add("5. **MISO's forecast product.** The Grid Status dataset is MISO's mid-term load forecast; I used the newest version of each hour (published 24-47 hours "
    "ahead). That may be older than MISO's true day-ahead forecast, which would make MISO look slightly worse than it is. Publish times in the "
    "data look like date stamps, not exact release times.")
add("6. **Weather source.** MERRA-2 reanalysis (0.5 x 0.625 degree grid), 8 points averaged equally. Population or load weighting, "
    "and more points, may help. Dew point from MERRA-2 was not used (see section 2).")
add("7. **Days excluded from every model:** the first 2 days of each summer (no lagged weather), any day with a missing load hour, and "
    "2026-08-31 (NASA solar data missing for its last 5 hours). Every model and MISO are scored on exactly the same days.")
add("8. **Filled load hours** come from MISO's own reports (a slightly different source than the 5-minute Grid Status data); validation was within 0.3% (median).")
add("")
add("## 7. Decisions needed from Dr. Holloway")
add("")
add("1. **Framing:** is it acceptable to headline the day-before (forecast) results and show same-day only as an upper bound, with the caveat in 6.1?")
add("2. **Level shift:** keep the fixed split plus walk-forward, or add a year adjustment (for example modelling the logarithm of load)?")
add("3. **What counts as meaningfully better:** I used a 95% block-bootstrap interval that excludes zero. Is that the right bar?")
add("4. **Next variables and weighting:** population-weighted weather, more MISO points, Heat Index, hour-of-peak analysis, and additional summers (the second pass).")
add("5. **Secondary question (2025 to 2026 jump):** not yet analysed; the data so far show 2026 was about 1.2 C warmer.")
add("")
add("## 8. Files")
add("")
add("- Tables (`outputs/tables/`): `model_comparison.csv`, `humidity_effect.csv`, `vs_miso.csv`, `best_params.csv`, "
    "`predictions_daily.csv`, `walk_forward_predictions.csv`, `feature_notes.csv`.")
add("- Figures (`outputs/figures/`): `fig_model_comparison.png`, `fig_humidity_effect.png`, `fig_pred_vs_actual_2026.png`, "
    "`fig_timeseries_2026.png`, plus `peak_vs_tmax.png` from the merge step.")
add("- Scripts (`code/`): `06_merge.py`, `08_forecast_daily.py`, `09_build_features.py`, `10_models.py`, `11_report.py`. LOG.md records every decision.")
add("")

(OUT_DIR / "RESULTS.md").write_text("\n".join(lines), encoding="utf-8")
print("Saved 4 figures and outputs/RESULTS.md")