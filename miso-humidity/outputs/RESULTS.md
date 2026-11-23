# Preliminary results: how close can NASA POWER weather get to MISO's daily peak load forecast?

*Generated automatically by `11_report.py` on 2026-11-23. Exploratory, two summers, 89 test days. Numbers are for the models exactly as specified in `10_models.py`; nothing was tuned on 2026.*

## 1. The short version

- **Question:** how close can a model built only on free NASA POWER weather get to MISO's own day-ahead forecast of daily peak summer load, and does adding humidity help?
- **Method:** models fitted on summer 2025 (90 days) and tested once on summer 2026 (89 days).
- **MISO's forecast** was off by 2.18 GW (RMSE; 1.62% on average) on those days.
- **Best case (the weather that actually happened on the day):** the regression with humidity was off by 2.45 GW (1.83%), the gradient boosting model with humidity by 3.75 GW (2.88%).
- **Forecast-style (only the previous day's weather):** 4.54 GW for the regression with humidity and 5.16 GW for gradient boosting with humidity. This is the like-for-like comparison with MISO's forecast, but yesterday's weather is a poor stand-in for tomorrow's weather forecast that MISO has.
- **Does humidity help?** Gradient boosting, same-day weather: RMSE 4.02 GW without humidity, 3.75 GW with (-0.27 GW, -6.7%; 95% interval -0.80 to +0.55 GW): no clear difference. Gradient boosting, day-before weather: RMSE 5.07 GW without humidity, 5.16 GW with (+0.09 GW, +1.7%; 95% interval -0.43 to +0.76 GW): no clear difference.
- **Read this as preliminary:** two summers, about 90 test days, and a 2025-to-2026 level shift all limit what can be concluded (section 6).

## 2. What was done

- **Load:** Grid Status `miso_load` (5-minute) averaged to hourly, gaps filled from MISO's own reports after a validation (median difference 0.3%). *Daily peak* = the highest hourly average in a US Central day, June 1 to Aug 31.
- **Weather:** NASA POWER hourly data (MERRA-2 reanalysis, requested in UTC) at 8 points across the MISO footprint (Minneapolis, Madison, Detroit, St. Louis, Des Moines, Indianapolis, New Orleans, Little Rock), averaged into one MISO-wide series. Variables: temperature (daily high), specific humidity, sunlight, wind, rain.
- **Humidity variable:** specific humidity (`QV2M`) rather than dew point. Dr. Holloway advised avoiding dew point because of known problems with MERRA-2 dew point; the data also showed hours with dew point above air temperature.
- **MISO benchmark:** Grid Status `miso_load_forecast_mid_term_by_region`. MISO publishes a new forecast every day; for every hour I used the newest version (published 24-47 hours earlier), summed the 10 zones, and took each day's highest hour.
- **Models:** (1) ordinary regression: temperature and temperature squared with day-of-week and holiday adjustments, then the same plus humidity; (2) machine learning (gradient boosting, the primary one, and random forest) with four nested sets of inputs: temperature only; + humidity; + sunlight, wind and rain; + previous-day temperature and heat-wave length.
- **Two weather timings:** *same-day* uses the weather of the day being predicted (a best case a real forecaster would not have a day ahead); *day-before* uses only the previous day's weather.
- **Scoring:** RMSE (typical error in GW; large misses count more), MAPE (average % error), R-squared, and bias (average prediction minus actual). Uncertainty on differences uses a block bootstrap (7-day blocks) because neighbouring days are related.
- **Two tests:** a *fixed split* (fit on 2025, predict 2026) and a *walk-forward* test (each 2026 day predicted from 2025 plus the 2026 days at least 2 days older), which lets models adapt to the 2026 load level.

## 3. Results on summer 2026

| Model | Weather | RMSE (GW) | MAPE (%) | R-squared | Bias (GW) | Walk-forward RMSE (GW) |
|---|---|---|---|---|---|---|
| Regression: temperature | same-day weather | 3.91 | 2.85 | 0.837 | +2.47 | 3.11 |
| Regression: + humidity | same-day weather | 2.45 | 1.83 | 0.936 | +0.21 | 2.43 |
| Gradient boosting: temperature | same-day weather | 4.02 | 3.07 | 0.828 | +1.79 | 3.31 |
| Gradient boosting: + humidity | same-day weather | 3.75 | 2.88 | 0.850 | +0.48 | 2.92 |
| Gradient boosting: + sun, wind, rain | same-day weather | 3.37 | 2.57 | 0.879 | +0.72 | 2.73 |
| Gradient boosting: + heat-wave features | same-day weather | 3.22 | 2.52 | 0.889 | +0.64 | 2.81 |
| Random forest: + humidity | same-day weather | 4.52 | 3.47 | 0.781 | +1.17 | 4.18 |
| Regression: temperature | day-before weather | 4.72 | 3.58 | 0.763 | +1.30 | 4.77 |
| Regression: + humidity | day-before weather | 4.54 | 3.42 | 0.780 | -0.67 | 4.66 |
| Gradient boosting: temperature | day-before weather | 5.07 | 3.86 | 0.725 | +0.73 | 5.00 |
| Gradient boosting: + humidity | day-before weather | 5.16 | 3.96 | 0.716 | -1.26 | 4.98 |
| Gradient boosting: + sun, wind, rain | day-before weather | 5.26 | 4.02 | 0.704 | -1.09 | 5.00 |
| Gradient boosting: + heat-wave features | day-before weather | 5.44 | 4.16 | 0.684 | -1.00 | 5.16 |
| Random forest: + humidity | day-before weather | 5.83 | 4.35 | 0.638 | -0.49 | 5.76 |
| **MISO day-ahead forecast** | (its own weather forecast) | **2.18** | **1.62** | **0.949** | **+0.86** | n/a |

All 20 models are in `outputs/tables/model_comparison.csv` (in-sample numbers included). Figures: `fig_model_comparison.png`, `fig_pred_vs_actual_2026.png`, `fig_timeseries_2026.png`.

## 4. Does humidity help?

Change in RMSE when specific humidity is added (negative = humidity helps). The interval is a 95% block-bootstrap interval; if it includes zero the data cannot tell the two models apart.

| Model | Weather | Test | RMSE without (GW) | RMSE with (GW) | Change (GW) | 95% interval (GW) | Verdict |
|---|---|---|---|---|---|---|---|
| Regression | same-day weather | fixed split | 3.91 | 2.45 | -1.45 | -2.09 to -0.52 | model with the added variables is better |
| Random forest | same-day weather | fixed split | 4.54 | 4.52 | -0.02 | -0.38 to +0.52 | no clear difference |
| Gradient boosting | same-day weather | fixed split | 4.02 | 3.75 | -0.27 | -0.80 to +0.55 | no clear difference |
| Regression | day-before weather | fixed split | 4.72 | 4.54 | -0.18 | -0.80 to +0.48 | no clear difference |
| Random forest | day-before weather | fixed split | 5.59 | 5.83 | +0.24 | -0.27 to +0.93 | no clear difference |
| Gradient boosting | day-before weather | fixed split | 5.07 | 5.16 | +0.09 | -0.43 to +0.76 | no clear difference |
| Regression | same-day weather | walk-forward | 3.11 | 2.43 | -0.68 | -1.04 to -0.13 | model with the added variables is better |
| Random forest | same-day weather | walk-forward | 3.92 | 4.18 | +0.26 | -0.14 to +0.55 | no clear difference |
| Gradient boosting | same-day weather | walk-forward | 3.31 | 2.92 | -0.40 | -0.78 to +0.29 | no clear difference |
| Regression | day-before weather | walk-forward | 4.77 | 4.66 | -0.11 | -0.49 to +0.22 | no clear difference |
| Random forest | day-before weather | walk-forward | 5.59 | 5.76 | +0.18 | -0.16 to +0.63 | no clear difference |
| Gradient boosting | day-before weather | walk-forward | 5.00 | 4.98 | -0.01 | -0.34 to +0.41 | no clear difference |

Figure: `fig_humidity_effect.png`. Adding sunlight, wind and rain, then heat-wave features, to the gradient boosting model (fixed split):

- Gradient boosting, same-day weather: RMSE 3.75 GW without sunlight, wind, rain, 3.37 GW with (-0.38 GW, -10.1%; 95% interval -0.77 to -0.06 GW): model with the added variables is better. (adds: sunlight, wind, rain)
- Gradient boosting, same-day weather: RMSE 3.37 GW without previous-day temperature, heat-wave length, 3.22 GW with (-0.15 GW, -4.5%; 95% interval -0.52 to +0.26 GW): no clear difference. (adds: previous-day temperature, heat-wave length)
- Gradient boosting, day-before weather: RMSE 5.16 GW without sunlight, wind, rain, 5.26 GW with (+0.10 GW, +2.0%; 95% interval -0.35 to +0.53 GW): no clear difference. (adds: sunlight, wind, rain)
- Gradient boosting, day-before weather: RMSE 5.26 GW without previous-day temperature, heat-wave length, 5.44 GW with (+0.18 GW, +3.4%; 95% interval -0.03 to +0.49 GW): no clear difference. (adds: previous-day temperature, heat-wave length)

## 5. How close to MISO?

Difference in RMSE between each model and MISO's forecast on the same days (positive = the model is further off than MISO; 95% block-bootstrap interval).

| Model | Weather | Test | Model RMSE (GW) | MISO RMSE (GW) | Difference (GW) | 95% interval (GW) | Verdict |
|---|---|---|---|---|---|---|---|
| Regression: + humidity | same-day weather | fixed split | 2.45 | 2.18 | +0.27 | -0.22 to +0.82 | no clear difference |
| Regression: + humidity | same-day weather | walk-forward | 2.43 | 2.18 | +0.25 | -0.39 to +0.97 | no clear difference |
| Gradient boosting: + humidity | same-day weather | fixed split | 3.75 | 2.18 | +1.57 | +0.67 to +2.12 | our model is worse |
| Gradient boosting: + humidity | same-day weather | walk-forward | 2.92 | 2.18 | +0.73 | +0.22 to +1.12 | our model is worse |
| Gradient boosting: + heat-wave features | same-day weather | fixed split | 3.22 | 2.18 | +1.04 | +0.33 to +1.45 | our model is worse |
| Gradient boosting: + heat-wave features | same-day weather | walk-forward | 2.81 | 2.18 | +0.63 | +0.01 to +1.00 | our model is worse |
| Regression: + humidity | day-before weather | fixed split | 4.54 | 2.18 | +2.36 | +1.52 to +3.31 | our model is worse |
| Regression: + humidity | day-before weather | walk-forward | 4.66 | 2.18 | +2.48 | +1.48 to +3.58 | our model is worse |
| Gradient boosting: + humidity | day-before weather | fixed split | 5.16 | 2.18 | +2.98 | +2.01 to +3.91 | our model is worse |
| Gradient boosting: + humidity | day-before weather | walk-forward | 4.98 | 2.18 | +2.80 | +1.97 to +3.60 | our model is worse |
| Gradient boosting: + heat-wave features | day-before weather | fixed split | 5.44 | 2.18 | +3.26 | +2.45 to +4.02 | our model is worse |
| Gradient boosting: + heat-wave features | day-before weather | walk-forward | 5.16 | 2.18 | +2.98 | +2.11 to +3.77 | our model is worse |

## 6. Caveats (please read before quoting any number)

1. **Observed vs. forecast weather.** NASA POWER describes weather that already happened. The *same-day* models are told the true weather, MISO's forecast had to predict it, so the comparison favours the models. The *day-before* models use a real forecast-style setup but with yesterday's weather instead of a weather forecast, so they are handicapped. The truth about what NASA data could support lies between the two.
2. **Level shift between summers.** Daily peaks were about 2.5% higher in 2026 and 2026 was also warmer. A model trained only on 2025 carries 2025's level into 2026: the bias column shows the average over- or under-prediction (MISO: +0.86 GW). The walk-forward test shows how much of this goes away when models may learn from earlier 2026 days. This is a description, not an explanation of the shift.
3. **Hotter days than the training summer.** Tree-based models cannot predict beyond the range they saw in training; if 2026 has hotter days than 2025, gradient boosting and random forest will under-predict them while the regression can extrapolate.
4. **Small sample.** About 90 days per summer. Differences of a few tenths of a GW between models are within noise; use the intervals.
5. **MISO's forecast product.** The Grid Status dataset is MISO's mid-term load forecast; I used the newest version of each hour (published 24-47 hours ahead). That may be older than MISO's true day-ahead forecast, which would make MISO look slightly worse than it is. Publish times in the data look like date stamps, not exact release times.
6. **Weather source.** MERRA-2 reanalysis (0.5 x 0.625 degree grid), 8 points averaged equally. Population or load weighting, and more points, may help. Dew point from MERRA-2 was not used (see section 2).
7. **Days excluded from every model:** the first 2 days of each summer (no lagged weather), any day with a missing load hour, and 2026-08-31 (NASA solar data missing for its last 5 hours). Every model and MISO are scored on exactly the same days.
8. **Filled load hours** come from MISO's own reports (a slightly different source than the 5-minute Grid Status data); validation was within 0.3% (median).

## 7. Decisions needed from Dr. Holloway

1. **Framing:** are results for same-day weather (best case) and day-before weather (forecast-style) both acceptable, with the caveat in 6.1?
2. **Level shift:** keep the fixed split plus walk-forward, or add a year adjustment (for example modelling the logarithm of load)?
3. **What counts as meaningfully better:** I used a 95% block-bootstrap interval that excludes zero. Is that the right bar?
4. **Next variables and weighting:** population-weighted weather, more MISO points, Heat Index, hour-of-peak analysis, and additional summers (the second pass).
5. **Secondary question (2025 to 2026 jump):** not yet analysed; the data so far show 2026 was about 1.2 C warmer.

## 8. Files

- Tables (`outputs/tables/`): `model_comparison.csv`, `humidity_effect.csv`, `vs_miso.csv`, `best_params.csv`, `predictions_daily.csv`, `walk_forward_predictions.csv`, `feature_notes.csv`.
- Figures (`outputs/figures/`): `fig_model_comparison.png`, `fig_humidity_effect.png`, `fig_pred_vs_actual_2026.png`, `fig_timeseries_2026.png`, plus `peak_vs_tmax.png` from the merge step.
- Scripts (`code/`): `06_merge.py`, `08_forecast_daily.py`, `09_build_features.py`, `10_models.py`, `11_report.py`. LOG.md records every decision.
