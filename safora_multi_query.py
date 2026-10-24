"""SAFORA multi-query Google Trends feature engineering.

Input CSV columns required: date, query, interest
Optional: source_file

Run:
  py safora_multi_query.py --input .\\data\\SAFORA_clean_monthly_trends.csv --output-dir .\\outputs

Important: Google Trends indices from separate exports may be normalized independently.
This script calculates features within each query and does not rank raw query levels against each other.
"""
from __future__ import annotations
import argparse, json
from pathlib import Path
import numpy as np
import pandas as pd

REQUIRED = {"date", "query", "interest"}

def safe_div(a, b, eps=1e-6):
    return a / (np.abs(b) + eps)

def add_features(group: pd.DataFrame) -> pd.DataFrame:
    g = group.sort_values("date").copy().reset_index(drop=True)
    x = pd.to_numeric(g["interest"], errors="coerce").clip(lower=0, upper=100)
    g["interest"] = x
    g["rolling_mean_3"] = x.rolling(3, min_periods=3).mean()
    g["rolling_mean_6"] = x.rolling(6, min_periods=6).mean()
    g["previous_mean_3"] = x.shift(3).rolling(3, min_periods=3).mean()
    # Avoid exaggerated percentage changes when the previous baseline is near zero.
    prev = g["previous_mean_3"]
    g["search_momentum"] = np.where(prev >= 5, (g["rolling_mean_3"] - prev) / prev, np.nan)
    g["momentum_baseline_too_low"] = prev.lt(5) | prev.isna()
    # Expanding historical median baseline uses only current/past observations.
    g["trend_baseline"] = x.expanding(min_periods=6).median()
    valid = x.notna().cumsum()
    above = x.gt(g["trend_baseline"])
    g["trend_consistency"] = above.where(g["trend_baseline"].notna()).astype(float).groupby(valid).transform("mean")
    # More straightforward trailing consistency over the last 6 periods.
    g["trend_consistency_6"] = (x > g["trend_baseline"]).rolling(6, min_periods=6).mean()
    g["volatility_std_6"] = x.rolling(6, min_periods=6).std()
    rolling_mean = x.rolling(6, min_periods=6).mean()
    g["volatility_cv_6"] = g["volatility_std_6"] / rolling_mean.replace(0, np.nan)
    # Spike score based on trailing median and MAD; current point is excluded from baseline.
    prior = x.shift(1)
    prior_med = prior.rolling(12, min_periods=6).median()
    prior_mad = (prior - prior_med).abs().rolling(12, min_periods=6).median()
    g["robust_spike_score"] = (x - prior_med) / (1.4826 * prior_mad.replace(0, np.nan))
    g["spike_risk_flag"] = (g["robust_spike_score"] >= 3.5).fillna(False)
    # Seasonality: compare with prior observations from same calendar month only.
    month = g["date"].dt.month
    seasonal = pd.Series(np.nan, index=g.index, dtype=float)
    for i in range(len(g)):
        past = x.iloc[:i][month.iloc[:i].values == month.iloc[i]]
        if len(past) >= 2:
            seasonal.iloc[i] = past.mean()
    g["seasonal_baseline_same_month"] = seasonal
    g["seasonal_lift"] = np.where(seasonal >= 5, (x - seasonal) / seasonal, np.nan)
    g["valid_observations_so_far"] = x.notna().cumsum()
    g["nonzero_observation_count_so_far"] = x.gt(0).cumsum()
    g["series_sparsity_so_far"] = 1 - g["nonzero_observation_count_so_far"] / g["valid_observations_so_far"].replace(0, np.nan)
    g["series_has_enough_history"] = g["valid_observations_so_far"] >= 24
    # Transparent within-query screening score only; not probability or sales forecast.
    # Require enough history and at least 18 non-zero months to avoid ranking sparse data.
    momentum_component = g["search_momentum"].clip(-1, 1).fillna(0)
    consistency_component = g["trend_consistency_6"].fillna(0)
    volatility_penalty = g["volatility_cv_6"].clip(0, 2).fillna(1) / 2
    raw_score = 50 + 30 * momentum_component + 25 * consistency_component - 15 * volatility_penalty
    enough_signal = (g["valid_observations_so_far"] >= 24) & (g["nonzero_observation_count_so_far"] >= 18)
    g["opportunity_screening_score"] = raw_score.clip(0, 100).where(enough_signal)
    g["prediction_reliability"] = np.select(
        [g["valid_observations_so_far"] < 12,
         g["nonzero_observation_count_so_far"] < 18,
         g["valid_observations_so_far"] < 24],
        ["low: under 12 observations", "low: insufficient non-zero observations", "limited: under 24 observations"],
        default="feature-ready; forecast still requires backtesting"
    )
    return g

def naive_backtest(group: pd.DataFrame) -> dict:
    """Expanding-origin 1-step naive baseline; use only if >=24 valid monthly points."""
    g = group.sort_values("date")
    x = pd.to_numeric(g["interest"], errors="coerce").dropna().to_numpy(dtype=float)
    if len(x) < 24:
        return {"backtest_status": "not_run", "reason": "Need at least 24 valid observations", "n_test": 0, "mae": None, "rmse": None}
    start = max(18, int(len(x) * 0.8))
    actual, pred = [], []
    for i in range(start, len(x)):
        # Seasonal-naive baseline when a year of history exists, otherwise last observation.
        p = x[i - 12] if i >= 12 else x[i - 1]
        pred.append(float(p)); actual.append(float(x[i]))
    err = np.asarray(actual) - np.asarray(pred)
    return {"backtest_status": "baseline_only", "reason": "Seasonal-naive baseline; not an ML model", "n_test": int(len(err)), "mae": float(np.mean(np.abs(err))), "rmse": float(np.sqrt(np.mean(err**2)))}

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--input", default=r".\data\SAFORA_clean_monthly_trends.csv")
    ap.add_argument("--output-dir", default=r".\outputs")
    args = ap.parse_args()
    in_path = Path(args.input); out_dir = Path(args.output_dir); out_dir.mkdir(parents=True, exist_ok=True)
    if not in_path.exists():
        raise SystemExit(f"Input file not found: {in_path.resolve()}")
    df = pd.read_csv(in_path)
    missing = REQUIRED - set(df.columns)
    if missing:
        raise SystemExit(f"CSV is missing required columns: {sorted(missing)}. Required: date, query, interest")
    df["date"] = pd.to_datetime(df["date"], errors="coerce")
    df["interest"] = pd.to_numeric(df["interest"], errors="coerce")
    df["query"] = df["query"].astype(str).str.strip()
    bad_dates = int(df["date"].isna().sum())
    bad_interest = int(df["interest"].isna().sum())
    df = df.dropna(subset=["date", "query", "interest"])
    df = df[df["query"].ne("")]
    # Deduplicate query/date; preserve mean if duplicated records exist.
    df = df.groupby(["query", "date"], as_index=False).agg(
        interest=("interest", "mean"),
        source_file=("source_file", lambda s: " | ".join(sorted(set(s.dropna().astype(str))))) if "source_file" in df.columns else ("query", "first")
    )
    features = pd.concat([add_features(g) for _, g in df.groupby("query", sort=True)], ignore_index=True)
    features = features.sort_values(["query", "date"])
    features.to_csv(out_dir / "safora_multi_query_features.csv", index=False)
    summaries = []
    for query, g in df.groupby("query", sort=True):
        bt = naive_backtest(g)
        x = g["interest"]
        summaries.append({
            "query": query, "observations": int(x.notna().sum()),
            "nonzero_observations": int(x.gt(0).sum()),
            "start_date": str(g["date"].min().date()), "end_date": str(g["date"].max().date()),
            "mean_interest_within_export": float(x.mean()), "latest_interest": float(g.sort_values("date")["interest"].iloc[-1]),
            "latest_momentum": (float(features.loc[features["query"].eq(query), "search_momentum"].dropna().iloc[-1]) if not features.loc[features["query"].eq(query), "search_momentum"].dropna().empty else None),
            "latest_opportunity_screening_score": (float(features.loc[features["query"].eq(query), "opportunity_screening_score"].dropna().iloc[-1]) if not features.loc[features["query"].eq(query), "opportunity_screening_score"].dropna().empty else None),
            **bt
        })
    summary_df = pd.DataFrame(summaries)
    summary_df.to_csv(out_dir / "safora_query_summary.csv", index=False)
    report = {
        "input_file": str(in_path), "rows_after_deduplication": int(len(df)), "queries": int(df["query"].nunique()),
        "invalid_dates_dropped": bad_dates, "invalid_interest_dropped": bad_interest,
        "outputs": ["safora_multi_query_features.csv", "safora_query_summary.csv", "safora_multi_query_report.json"],
        "important_limitations": [
            "Google Trends values are relative-interest indices, not absolute search counts.",
            "Separate exports may be independently normalized; do not compare raw interest levels across queries unless exported together under a common comparison.",
            "Opportunity screening score is a heuristic, not a probability of sales or success.",
            "Cross-platform confirmation, events, regional concentration, pricing, competition, and sales are not inferred when absent from the input.",
            "Backtest is only a seasonal-naive baseline, not a trained ML model; monthly history is short for robust evaluation."
        ], "query_summaries": summaries
    }
    (out_dir / "safora_multi_query_report.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps({"status": "success", "input_rows": int(len(df)), "queries": int(df["query"].nunique()), "features_output": str(out_dir / "safora_multi_query_features.csv"), "summary_output": str(out_dir / "safora_query_summary.csv"), "report_output": str(out_dir / "safora_multi_query_report.json"), "query_summary": summaries}, indent=2))
    print("\nDone. Review the report; do not treat the heuristic score as a sales probability.")
if __name__ == "__main__":
    main()
