"""
10_models.py

Fits the models, scores them, and compares them with MISO's day-ahead forecast.

Reads:   data/processed/model_table_same_day.csv, model_table_day_before.csv   (from 09_build_features.py)
Writes:  outputs/tables/model_comparison.csv      every model, in-sample and out-of-sample metrics
         outputs/tables/humidity_effect.csv       does adding humidity (and other variables) help?
         outputs/tables/vs_miso.csv               every model minus MISO's forecast, with uncertainty
         outputs/tables/best_params.csv           settings chosen by cross-validation inside 2025
         outputs/tables/predictions_daily.csv     daily predictions of every model (train and test days)
         outputs/tables/walk_forward_predictions.csv

Run:  python3 10_models.py                         (full run, a few minutes because of the walk-forward step)
      python3 10_models.py --skip-walk-forward     (quick run)

DESIGN (fixed before results; see LOG.md 2026-11-23)
  Target       daily peak load (highest hourly mean, MW) of each Central day, June 1 - Aug 31.
  Train/test   fit on summer 2025; test once on summer 2026. Nothing about 2026 is used to choose
               features, settings or thresholds.
  Weather      two versions: "same_day" (weather of day D, best case) and "day_before" (weather of day D-1,
               a real forecast-style setup; the MAIN comparison with MISO's forecast).
  Models       Regression (plain least squares, easy to explain):
                 R1  peak ~ tmax + tmax^2 + day of week + holiday
                 R2  R1 + specific humidity + tmax x humidity
               Machine learning (Random forest = RF, Gradient boosting = GBM; GBM is the primary ML model):
                 E1 temperature only        E2 + humidity       E3 + sunlight, wind, rain
                 E4 + previous-day temperature and heat-wave length
               All ML models also get day of week and holiday. E1 -> E2 is the humidity question.
  Settings     ML settings come from a small grid, chosen by 5-fold cross-validation INSIDE 2025
               (contiguous blocks of days). Then the model is refit on all of 2025.
  Walk-forward A second, more realistic test: for every 2026 day, refit on 2025 + the 2026 days that are at
               least 2 days older (MISO's newest forecast is 24-47 hours old), then predict that day. This
               lets the models learn from the 2026 level without ever seeing the day they predict.
  Metrics      RMSE, MAE (MW), MAPE (%), R^2, and bias (mean of prediction minus actual, MW).
  Uncertainty  moving-block bootstrap (7-day blocks, 2,000 resamples) for differences in RMSE, because
               neighbouring days are not independent.
"""

import sys
import time
import warnings
from pathlib import Path

import numpy as np
import pandas as pd
import sklearn
from sklearn.ensemble import GradientBoostingRegressor, RandomForestRegressor
from sklearn.linear_model import LinearRegression
from sklearn.model_selection import GridSearchCV, KFold

PROJECT_ROOT = Path(__file__).resolve().parent.parent
PROC_DIR = PROJECT_ROOT / "data" / "processed"
TABLE_DIR = PROJECT_ROOT / "outputs" / "tables"
TABLE_DIR.mkdir(parents=True, exist_ok=True)

SEED = 42
TRAIN_YEAR, TEST_YEAR = 2025, 2026
WALK_FORWARD = "--skip-walk-forward" not in sys.argv
WF_GAP_DAYS = 2
N_BOOT, BLOCK = 2000, 7

CAL = [f"dow_{d}" for d in range(1, 7)] + ["holiday"]
FEATURE_SETS = {
    "E1_temp": ["tmax"] + CAL,
    "E2_humidity": ["tmax", "qv_mean"] + CAL,
    "E3_expanded": ["tmax", "qv_mean", "solar_mean", "ws_mean", "precip_sum"] + CAL,
    "E4_engineered": ["tmax", "qv_mean", "solar_mean", "ws_mean", "precip_sum", "tmax_prev", "heat_streak"] + CAL,
}
RF_GRID = {"max_depth": [3, 5, None], "min_samples_leaf": [2, 5]}
GBM_GRID = {"n_estimators": [100, 300], "max_depth": [2, 3]}

TIMINGS = {"same_day": "model_table_same_day.csv", "day_before": "model_table_day_before.csv"}

SPECS = [("R1_regression_temp", "REG", "R1"), ("R2_regression_humidity", "REG", "R2")]
for fam in ("RF", "GBM"):
    for key in FEATURE_SETS:
        SPECS.append((f"{fam}_{key}", fam, key))

# pairs for "does adding X help?": (model without, model with, label, what is added)
COMPARISONS = [
    ("R1_regression_temp", "R2_regression_humidity", "Regression", "humidity"),
    ("RF_E1_temp", "RF_E2_humidity", "Random forest", "humidity"),
    ("GBM_E1_temp", "GBM_E2_humidity", "Gradient boosting", "humidity"),
    ("RF_E2_humidity", "RF_E3_expanded", "Random forest", "sunlight, wind, rain"),
    ("GBM_E2_humidity", "GBM_E3_expanded", "Gradient boosting", "sunlight, wind, rain"),
    ("RF_E3_expanded", "RF_E4_engineered", "Random forest", "previous-day temperature, heat-wave length"),
    ("GBM_E3_expanded", "GBM_E4_engineered", "Gradient boosting", "previous-day temperature, heat-wave length"),
]

warnings.filterwarnings("ignore", category=FutureWarning)
print(f"Versions: python-sklearn {sklearn.__version__}, pandas {pd.__version__}, numpy {np.__version__}")


# --------------------------------------------------------------------------------------
# Helpers
# --------------------------------------------------------------------------------------
def metrics(y, p):
    e = p - y
    return {
        "rmse": float(np.sqrt(np.mean(e ** 2))),
        "mae": float(np.mean(np.abs(e))),
        "mape": float(np.mean(np.abs(e) / y) * 100),
        "r2": float(1 - np.sum(e ** 2) / np.sum((y - y.mean()) ** 2)),
        "bias": float(np.mean(e)),
    }


def reg_matrix(df, kind, centers):
    """Regression inputs. Temperature is centred on the TRAINING mean so tmax and tmax^2 are well behaved."""
    tc = df["tmax"] - centers["tmax"]
    X = pd.DataFrame({"tmax_c": tc, "tmax_c_sq": tc ** 2}, index=df.index)
    if kind == "R2":
        qc = df["qv_mean"] - centers["qv_mean"]
        X["qv_c"] = qc
        X["tmax_x_qv"] = tc * qc
    for c in CAL:
        X[c] = df[c]
    return X.to_numpy(dtype=float)


def make_ml(family):
    if family == "RF":
        return RandomForestRegressor(n_estimators=200, random_state=SEED, n_jobs=1)
    return GradientBoostingRegressor(learning_rate=0.05, subsample=0.8, random_state=SEED)


def tune(train, family, fs):
    """Choose settings by cross-validation inside the training summer only."""
    grid = RF_GRID if family == "RF" else GBM_GRID
    search = GridSearchCV(make_ml(family), grid, cv=KFold(n_splits=5, shuffle=False),
                          scoring="neg_root_mean_squared_error", n_jobs=1)
    search.fit(train[FEATURE_SETS[fs]].to_numpy(dtype=float), train["peak_mw"].to_numpy(dtype=float))
    return search.best_params_, float(-search.best_score_)


def fit_predict(train, targets, family, fs, params):
    """Fit on `train`, return one prediction array for each dataframe in `targets`."""
    y = train["peak_mw"].to_numpy(dtype=float)
    if family == "REG":
        centers = {"tmax": train["tmax"].mean(), "qv_mean": train["qv_mean"].mean()}
        model = LinearRegression().fit(reg_matrix(train, fs, centers), y)
        return [model.predict(reg_matrix(d, fs, centers)) for d in targets]
    model = make_ml(family).set_params(**params)
    model.fit(train[FEATURE_SETS[fs]].to_numpy(dtype=float), y)
    return [model.predict(d[FEATURE_SETS[fs]].to_numpy(dtype=float)) for d in targets]


def block_boot_diff(err_a, err_b, seed=SEED):
    """95% interval for RMSE(a) - RMSE(b), resampling blocks of consecutive days."""
    n = len(err_a)
    rng = np.random.default_rng(seed)
    n_blocks = int(np.ceil(n / BLOCK))
    diffs = np.empty(N_BOOT)
    for b in range(N_BOOT):
        starts = rng.integers(0, n - BLOCK + 1, n_blocks)
        idx = np.concatenate([np.arange(s, s + BLOCK) for s in starts])[:n]
        diffs[b] = np.sqrt(np.mean(err_a[idx] ** 2)) - np.sqrt(np.mean(err_b[idx] ** 2))
    return float(np.percentile(diffs, 2.5)), float(np.percentile(diffs, 97.5))


def verdict(lo, hi):
    if hi < 0:
        return "first model is better"
    if lo > 0:
        return "first model is worse"
    return "no clear difference"


# --------------------------------------------------------------------------------------
# Fit everything
# --------------------------------------------------------------------------------------
rows, param_rows = [], []
pred_fixed, pred_wf = {}, {}        # pred_fixed[timing][model_id] -> array on the 2026 days
pred_all = {}                       # every day (2025 in-sample + 2026 out-of-sample), for predictions_daily.csv
test_index, actual_test, miso_test = None, None, None
t0 = time.time()

for timing, fname in TIMINGS.items():
    path = PROC_DIR / fname
    if not path.exists():
        sys.exit(f"Missing {path}. Run 09_build_features.py first.")
    tab = pd.read_csv(path, index_col="local_day", parse_dates=["local_day"]).sort_index()
    train = tab[tab["year"] == TRAIN_YEAR]
    test = tab[tab["year"] == TEST_YEAR]
    assert len(train) > 20 and len(test) > 20
    assert train.index.max() < test.index.min(), "training days must all come before the test days"

    if test_index is None:
        test_index, actual_test, miso_test = test.index, test["peak_mw"].to_numpy(), test["forecast_peak_mw"].to_numpy()
    else:
        assert test.index.equals(test_index), "both weather versions must use the same test days"
    y_train, y_test = train["peak_mw"].to_numpy(), test["peak_mw"].to_numpy()

    pred_fixed[timing], pred_wf[timing], pred_all[timing] = {}, {}, {}
    print(f"\n=== weather timing: {timing}  (train {len(train)} days of {TRAIN_YEAR}, test {len(test)} days of {TEST_YEAR}) ===")

    for model_id, family, fs in SPECS:
        params, cv_rmse = {}, np.nan
        if family != "REG":
            params, cv_rmse = tune(train, family, fs)
            param_rows.append({"timing": timing, "model": model_id, "cv_rmse_2025": cv_rmse, **{k: str(v) for k, v in params.items()}})
        p_train, p_test = fit_predict(train, [train, test], family, fs, params)
        pred_fixed[timing][model_id] = p_test
        pred_all[timing][model_id] = pd.Series(np.concatenate([p_train, p_test]), index=train.index.append(test.index))

        row = {"timing": timing, "model": model_id, "family": family, "n_train": len(train), "n_test": len(test),
               "cv_rmse_2025": cv_rmse, "settings": str(params) if params else ""}
        for k, v in metrics(y_train, p_train).items():
            row[f"train_{k}"] = v
        for k, v in metrics(y_test, p_test).items():
            row[f"test_{k}"] = v

        if WALK_FORWARD:
            wf = []
            for day in test.index:
                tr = tab[tab.index <= day - pd.Timedelta(days=WF_GAP_DAYS)]
                # guards: never train on the day being predicted, the day before it, or anything later
                assert tr.index.max() <= day - pd.Timedelta(days=WF_GAP_DAYS) and day not in tr.index and len(tr) > 30
                wf.append(fit_predict(tr, [test.loc[[day]]], family, fs, params)[0][0])
            wf = np.array(wf)
            pred_wf[timing][model_id] = wf
            for k, v in metrics(y_test, wf).items():
                row[f"wf_{k}"] = v
        rows.append(row)
        print(f"  {model_id:<26} test RMSE {row['test_rmse'] / 1000:6.2f} GW   MAPE {row['test_mape']:5.2f}%   "
              f"bias {row['test_bias'] / 1000:+6.2f} GW   ({time.time() - t0:5.0f}s)")

# MISO's own forecast on the same days (it is not fitted to anything here)
tab_sd = pd.read_csv(PROC_DIR / TIMINGS["same_day"], index_col="local_day", parse_dates=["local_day"]).sort_index()
miso_row = {"timing": "n/a", "model": "MISO_day_ahead_forecast", "family": "MISO",
            "n_train": int((tab_sd["year"] == TRAIN_YEAR).sum()), "n_test": len(test_index)}
tr_part = tab_sd[tab_sd["year"] == TRAIN_YEAR]
for k, v in metrics(tr_part["peak_mw"].to_numpy(), tr_part["forecast_peak_mw"].to_numpy()).items():
    miso_row[f"train_{k}"] = v        # "train" columns = the same days as our training summer (2025)
for k, v in metrics(actual_test, miso_test).items():
    miso_row[f"test_{k}"] = v
rows.append(miso_row)
print(f"\n  {'MISO forecast':<26} test RMSE {miso_row['test_rmse'] / 1000:6.2f} GW   MAPE {miso_row['test_mape']:5.2f}%   "
      f"bias {miso_row['test_bias'] / 1000:+6.2f} GW")

comparison = pd.DataFrame(rows)
comparison.to_csv(TABLE_DIR / "model_comparison.csv", index=False)
pd.DataFrame(param_rows).to_csv(TABLE_DIR / "best_params.csv", index=False)

# --------------------------------------------------------------------------------------
# Does adding humidity (or other variables) help? And how far are we from MISO?
# --------------------------------------------------------------------------------------
eff_rows, miso_rows = [], []
for timing in TIMINGS:
    modes = [("fixed split (train 2025, test 2026)", pred_fixed[timing])]
    if WALK_FORWARD:
        modes.append(("walk-forward", pred_wf[timing]))
    for mode_name, preds in modes:
        for without, with_, label, added in COMPARISONS:
            e_a = preds[with_] - actual_test            # "with" minus truth
            e_b = preds[without] - actual_test
            rmse_with, rmse_without = np.sqrt(np.mean(e_a ** 2)), np.sqrt(np.mean(e_b ** 2))
            lo, hi = block_boot_diff(e_a, e_b)
            eff_rows.append({"timing": timing, "evaluation": mode_name, "model_family": label, "added": added,
                             "rmse_without_mw": rmse_without, "rmse_with_mw": rmse_with,
                             "delta_mw": rmse_with - rmse_without, "delta_pct": (rmse_with / rmse_without - 1) * 100,
                             "ci_low_mw": lo, "ci_high_mw": hi,
                             "verdict": verdict(lo, hi).replace("first model", "model with the added variables")})
        e_miso = miso_test - actual_test
        for model_id, _, _ in SPECS:
            e_m = preds[model_id] - actual_test
            lo, hi = block_boot_diff(e_m, e_miso)
            miso_rows.append({"timing": timing, "evaluation": mode_name, "model": model_id,
                              "rmse_model_mw": np.sqrt(np.mean(e_m ** 2)), "rmse_miso_mw": np.sqrt(np.mean(e_miso ** 2)),
                              "delta_mw": np.sqrt(np.mean(e_m ** 2)) - np.sqrt(np.mean(e_miso ** 2)),
                              "ci_low_mw": lo, "ci_high_mw": hi,
                              "verdict": verdict(lo, hi).replace("first model", "our model")})

pd.DataFrame(eff_rows).to_csv(TABLE_DIR / "humidity_effect.csv", index=False)
pd.DataFrame(miso_rows).to_csv(TABLE_DIR / "vs_miso.csv", index=False)

# --------------------------------------------------------------------------------------
# Daily predictions for the figures
# --------------------------------------------------------------------------------------
frame = tab_sd[["year", "peak_mw", "forecast_peak_mw"]].rename(columns={"peak_mw": "actual_mw", "forecast_peak_mw": "miso_forecast_mw"})
for timing in TIMINGS:
    for model_id, series in pred_all[timing].items():
        frame[f"{timing}__{model_id}"] = series
frame.to_csv(TABLE_DIR / "predictions_daily.csv")

if WALK_FORWARD:
    wf_frame = pd.DataFrame({"actual_mw": actual_test, "miso_forecast_mw": miso_test}, index=test_index)
    for timing in TIMINGS:
        for model_id, arr in pred_wf[timing].items():
            wf_frame[f"{timing}__{model_id}"] = arr
    wf_frame.index.name = "local_day"
    wf_frame.to_csv(TABLE_DIR / "walk_forward_predictions.csv")

print(f"\nDone in {time.time() - t0:.0f} seconds. Saved model_comparison.csv, humidity_effect.csv, vs_miso.csv, "
      "best_params.csv, predictions_daily.csv" + (", walk_forward_predictions.csv" if WALK_FORWARD else ""))
