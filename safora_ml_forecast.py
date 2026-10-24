"""SAFORA small-data ML forecasting experiment.

Uses past-only lag/rolling features and expanding-window walk-forward evaluation.
Compares RandomForestRegressor with a seasonal-naive baseline on the same test rows.
This is an experimental model, not a sales-demand predictor.
"""
from __future__ import annotations
import argparse
import json
from pathlib import Path
import warnings

import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestRegressor
from sklearn.metrics import mean_absolute_error, mean_squared_error


def build_features(group: pd.DataFrame) -> pd.DataFrame:
    g = group.sort_values("date").copy().reset_index(drop=True)
    y = pd.to_numeric(g["interest"], errors="coerce")
    g["target"] = y
    # All predictors use observations available strictly before the target month.
    for lag in (1, 2, 3, 6, 12):
        g[f"lag_{lag}"] = y.shift(lag)
    prior = y.shift(1)
    g["rolling_mean_3"] = prior.rolling(3, min_periods=3).mean()
    g["rolling_mean_6"] = prior.rolling(6, min_periods=6).mean()
    g["rolling_std_6"] = prior.rolling(6, min_periods=6).std(ddof=0)
    month = pd.to_datetime(g["date"]).dt.month
    g["month_sin"] = np.sin(2 * np.pi * month / 12)
    g["month_cos"] = np.cos(2 * np.pi * month / 12)
    # Seasonal naive predicts the same month from one year earlier.
    g["seasonal_naive"] = y.shift(12)
    return g


def metrics(actual, predicted):
    if len(actual) == 0:
        return {"mae": None, "rmse": None}
    return {
        "mae": float(mean_absolute_error(actual, predicted)),
        "rmse": float(np.sqrt(mean_squared_error(actual, predicted))),
    }


def run(input_path: Path, output_dir: Path, test_months: int):
    output_dir.mkdir(parents=True, exist_ok=True)
    raw = pd.read_csv(input_path)
    required = {"date", "query", "interest"}
    missing = required - set(raw.columns)
    if missing:
        raise ValueError(f"Input CSV missing required columns: {sorted(missing)}")
    raw["date"] = pd.to_datetime(raw["date"], errors="coerce")
    raw["interest"] = pd.to_numeric(raw["interest"], errors="coerce")
    raw = raw.dropna(subset=["date", "query", "interest"])
    raw["query"] = raw["query"].astype(str)
    # Ensure one observation per query/month; fail rather than silently double-count.
    dup = raw.duplicated(["query", "date"], keep=False)
    if dup.any():
        examples = raw.loc[dup, ["query", "date"]].head(5).to_dict("records")
        raise ValueError(f"Duplicate query/date rows found. Resolve duplicates first. Examples: {examples}")

    feature_cols = ["lag_1", "lag_2", "lag_3", "lag_6", "lag_12",
                    "rolling_mean_3", "rolling_mean_6", "rolling_std_6",
                    "month_sin", "month_cos"]
    all_preds, summaries = [], []
    warnings_list = []
    for query, group in raw.groupby("query", sort=True):
        g = build_features(group)
        g = g.sort_values("date").reset_index(drop=True)
        if len(g) <= 12 + 12:
            warnings_list.append(f"{query}: limited history; fewer than 25 monthly rows.")
        test_start = max(12, len(g) - test_months)
        # Fixed last test_months; only score rows for which both models can be evaluated.
        pred_rows = []
        for i in range(test_start, len(g)):
            row = g.iloc[i]
            if pd.isna(row["seasonal_naive"]) or row[feature_cols].isna().any():
                continue
            train = g.iloc[:i].dropna(subset=["target"] + feature_cols)
            if len(train) < 18:
                continue
            model = RandomForestRegressor(
                n_estimators=300, max_depth=5, min_samples_leaf=2,
                max_features=0.9, random_state=42, n_jobs=-1
            )
            model.fit(train[feature_cols], train["target"])
            pred = float(model.predict(row[feature_cols].to_frame().T)[0])
            pred = float(np.clip(pred, 0, 100))
            pred_rows.append({
                "query": query,
                "date": row["date"].date().isoformat(),
                "actual_interest": float(row["target"]),
                "seasonal_naive_prediction": float(row["seasonal_naive"]),
                "random_forest_prediction": pred,
                "training_rows": int(len(train)),
            })
        pred_df = pd.DataFrame(pred_rows)
        all_preds.extend(pred_rows)
        if len(pred_df):
            actual = pred_df["actual_interest"].to_numpy()
            base = metrics(actual, pred_df["seasonal_naive_prediction"].to_numpy())
            ml = metrics(actual, pred_df["random_forest_prediction"].to_numpy())
            winner = "random_forest" if ml["mae"] < base["mae"] else "seasonal_naive_or_tie"
            improvement = None if base["mae"] == 0 else float((base["mae"] - ml["mae"]) / base["mae"] * 100)
            status = "evaluated"
        else:
            base = {"mae": None, "rmse": None}
            ml = {"mae": None, "rmse": None}
            winner, improvement, status = "not_enough_trainable_rows", None, "insufficient_data"
            warnings_list.append(f"{query}: not enough trainable rows for a fair comparison.")
        summaries.append({
            "query": query,
            "observations": int(len(g)),
            "test_months_requested": int(test_months),
            "test_rows_scored": int(len(pred_df)),
            "baseline_mae": base["mae"],
            "baseline_rmse": base["rmse"],
            "random_forest_mae": ml["mae"],
            "random_forest_rmse": ml["rmse"],
            "mae_improvement_percent_vs_baseline": improvement,
            "better_on_test_mae": winner,
            "status": status,
        })

    pred_path = output_dir / "safora_ml_forecast_predictions.csv"
    summary_path = output_dir / "safora_ml_forecast_summary.csv"
    report_path = output_dir / "safora_ml_forecast_report.json"
    pd.DataFrame(all_preds).to_csv(pred_path, index=False)
    pd.DataFrame(summaries).to_csv(summary_path, index=False)
    report = {
        "status": "success",
        "input_file": str(input_path),
        "input_rows_after_validation": int(len(raw)),
        "queries": int(raw["query"].nunique()),
        "method": "Expanding-window walk-forward evaluation; past-only lag/rolling features",
        "models_compared": ["seasonal_naive", "RandomForestRegressor"],
        "test_months_requested": int(test_months),
        "features": feature_cols,
        "warnings": warnings_list,
        "limitations": [
            "This predicts relative Google Trends interest, not sales, customers, revenue, or market size.",
            "Only 61 monthly observations per query: results are experimental and may be unstable.",
            "Separate Google Trends exports may be normalized independently; do not compare raw levels across queries as market size.",
            "No future forecast is produced by this evaluation script; first inspect out-of-sample results.",
            "Random forest is accepted only if it beats the baseline on held-out MAE; no accuracy claim is implied."
        ],
        "outputs": {
            "predictions": str(pred_path),
            "summary": str(summary_path),
        },
        "summary": summaries,
    }
    report_path.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps({
        "status": "success",
        "input_rows": int(len(raw)),
        "queries": int(raw["query"].nunique()),
        "predictions_output": str(pred_path),
        "summary_output": str(summary_path),
        "report_output": str(report_path),
        "summary": summaries,
        "warnings": warnings_list,
    }, indent=2))
    print("\nDone. Compare Random Forest against the baseline; do not treat search interest as sales prediction.")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", default=r".\data\SAFORA_clean_monthly_trends.csv")
    parser.add_argument("--output-dir", default=r".\outputs")
    parser.add_argument("--test-months", type=int, default=13)
    args = parser.parse_args()
    if args.test_months < 1:
        raise SystemExit("--test-months must be >= 1")
    run(Path(args.input), Path(args.output_dir), args.test_months)

if __name__ == "__main__":
    warnings.filterwarnings("ignore", category=FutureWarning)
    main()
