"""
SAFORA Advanced Feature Engineering
===================================
Run from the folder containing this script:
    python safora_feature_engineering.py --data-dir ./data --output-dir ./outputs

Supports:
- Google Trends CSV (date/time + interest column; optional title/state/category columns)
- Anime metadata CSV (e.g. anime_dataset.csv)
- IMDb ratings TSV.GZ (optional)
- Video-game sales CSV/ZIP (optional)
- Optional events.csv and cross_platform.csv for event lift and cross-platform confirmation.

Important: Google Trends values are normalized relative-interest indices, NOT absolute search counts.
The script does not fabricate regional/platform/event data. Unsupported features are left NaN
and marked unavailable in the report.
"""
from __future__ import annotations
import argparse
import json
import re
import zipfile
from pathlib import Path
from typing import Optional

import numpy as np
import pandas as pd


DATE_CANDIDATES = ["date", "time", "week", "month", "timestamp", "period"]
VALUE_CANDIDATES = ["interest", "value", "search_interest", "trend", "score", "titles and franchise"]
TITLE_CANDIDATES = ["title", "anime", "name", "query", "keyword", "titles and franchise"]
STATE_CANDIDATES = ["state", "region", "geo", "province", "subregion"]
CATEGORY_CANDIDATES = ["query_category", "search_category", "category", "entity_type", "search_type"]


def norm(s):
    return re.sub(r"[^a-z0-9]+", "_", str(s).strip().lower()).strip("_")


def find_col(df, candidates):
    lookup = {norm(c): c for c in df.columns}
    for cand in candidates:
        if norm(cand) in lookup:
            return lookup[norm(cand)]
    # allow partial matches for common variations
    for col in df.columns:
        nc = norm(col)
        if any(norm(c) in nc for c in candidates):
            return col
    return None


def read_csv_flexible(path):
    try:
        return pd.read_csv(path)
    except UnicodeDecodeError:
        return pd.read_csv(path, encoding="latin-1")


def load_game_sales(path):
    if not path or not Path(path).exists():
        return None
    path = Path(path)
    if path.suffix.lower() == ".zip":
        with zipfile.ZipFile(path) as zf:
            candidates = [n for n in zf.namelist() if n.lower().endswith(".csv")]
            if not candidates:
                return None
            with zf.open(candidates[0]) as f:
                return pd.read_csv(f)
    return read_csv_flexible(path)


def safe_float(s):
    return pd.to_numeric(s, errors="coerce")


def gini(values):
    """Gini on non-negative, comparable normalized regional observations."""
    x = np.asarray(values, dtype=float)
    x = x[np.isfinite(x)]
    if len(x) < 2 or np.any(x < 0) or x.sum() <= 0:
        return np.nan
    x = np.sort(x)
    n = len(x)
    return float((2 * np.sum((np.arange(1, n + 1) * x)) / (n * x.sum())) - (n + 1) / n)


def engineer_trends(trends, events=None, cross_platform=None):
    df = trends.copy()
    date_col = find_col(df, DATE_CANDIDATES)
    value_col = find_col(df, VALUE_CANDIDATES)
    if date_col is None or value_col is None:
        raise ValueError(
            "Trends CSV must have a date/time column and a numeric interest column. "
            f"Found columns: {list(df.columns)}"
        )
    title_col = find_col(df, TITLE_CANDIDATES)
    if title_col == value_col:
        title_col = None
    state_col = find_col(df, STATE_CANDIDATES)
    category_col = find_col(df, CATEGORY_CANDIDATES)

    df["_date"] = pd.to_datetime(df[date_col], errors="coerce")
    df["_interest"] = safe_float(df[value_col])
    df = df.dropna(subset=["_date", "_interest"]).copy()
    df["_title"] = df[title_col].astype(str) if title_col else "ALL_TRENDS_SERIES"
    df["_state"] = df[state_col].astype(str) if state_col else "ALL_REGIONS"
    df["_category"] = df[category_col].astype(str) if category_col else "unknown"
    df = df.sort_values(["_title", "_state", "_date"]).reset_index(drop=True)

    groups = []
    for (title, state), g in df.groupby(["_title", "_state"], dropna=False, sort=False):
        g = g.sort_values("_date").copy()
        x = g["_interest"].astype(float)
        g["rolling_mean_3"] = x.rolling(3, min_periods=1).mean()
        g["rolling_mean_6"] = x.rolling(6, min_periods=2).mean()
        g["previous_mean_3"] = x.shift(3).rolling(3, min_periods=1).mean()
        eps = 1.0  # Stabilizer appropriate for 0-100 Trends indices; prevents division by near-zero.
        g["search_momentum"] = (g["rolling_mean_3"] - g["previous_mean_3"]) / (g["previous_mean_3"].abs() + eps)
        g["search_momentum"] = g["search_momentum"].replace([np.inf, -np.inf], np.nan)

        baseline = x.expanding(min_periods=3).median()
        g["trend_baseline"] = baseline
        valid = x.notna()
        above = (x > baseline) & baseline.notna()
        g["trend_consistency"] = above.astype(float).where(valid).expanding().mean()

        rolling_std = x.rolling(6, min_periods=3).std()
        rolling_avg = x.rolling(6, min_periods=3).mean()
        g["volatility_std_6"] = rolling_std
        g["volatility_cv_6"] = rolling_std / (rolling_avg.abs() + eps)
        med = x.rolling(12, min_periods=4).median()
        mad = (x - med).abs().rolling(12, min_periods=4).median()
        g["robust_spike_score"] = (x - med) / (1.4826 * mad + eps)
        g["spike_risk_flag"] = (g["robust_spike_score"] >= 3).astype("Int64")

        # Seasonal lift: compare each observation with the same calendar month across prior years.
        g["_month"] = g["_date"].dt.month
        seasonal_mean = g.groupby("_month")["_interest"].transform(
            lambda s: s.shift(1).expanding(min_periods=1).mean()
        )
        g["seasonal_baseline_same_month"] = seasonal_mean
        g["seasonal_lift"] = (x - seasonal_mean) / (seasonal_mean.abs() + eps)

        # Confidence/data sufficiency flags prevent overclaiming with short or sparse series.
        g["valid_observations_so_far"] = np.arange(1, len(g) + 1)
        g["series_has_enough_history"] = g["valid_observations_so_far"] >= 12
        g["nonzero_observation_count_so_far"] = (x > 0).cumsum()
        g["series_sparsity_so_far"] = 1 - ((x > 0).cumsum() / g["valid_observations_so_far"])
        groups.append(g)
    out = pd.concat(groups, ignore_index=True) if groups else df

    # Regional concentration: only calculate for a date/title with >=2 regional rows.
    out["regional_gini"] = np.nan
    if state_col:
        for (_, _), idx in out.groupby(["_title", "_date"]).groups.items():
            vals = out.loc[idx, "_interest"]
            if vals.notna().sum() >= 2:
                out.loc[idx, "regional_gini"] = gini(vals)
    out["regional_concentration_available"] = bool(state_col and out.groupby(["_title", "_date"])["_state"].nunique().ge(2).any())

    # Search diversity: requires distinct query categories for the same title/date.
    out["search_category_count"] = np.nan
    out["search_diversity_available"] = False
    if category_col:
        counts = out.groupby(["_title", "_date"])["_category"].transform("nunique")
        out["search_category_count"] = counts
        out["search_diversity_available"] = counts > 1

    # Event lift: requires events.csv with event_date and (optionally) title.
    out["event_lift"] = np.nan
    out["event_nearby"] = False
    if events is not None and not events.empty:
        ev = events.copy()
        ev_date_col = find_col(ev, ["event_date", "date", "start_date"])
        ev_title_col = find_col(ev, TITLE_CANDIDATES)
        if ev_date_col:
            ev["_event_date"] = pd.to_datetime(ev[ev_date_col], errors="coerce")
            ev = ev.dropna(subset=["_event_date"])
            for idx, row in out.iterrows():
                cand = ev
                if ev_title_col:
                    cand = cand[cand[ev_title_col].astype(str).str.casefold().eq(str(row["_title"]).casefold())]
                if not cand.empty:
                    days = (cand["_event_date"] - row["_date"]).dt.days.abs()
                    near = days <= 14
                    if near.any():
                        out.loc[idx, "event_nearby"] = True
                        # Event lift is observation vs its existing rolling baseline, not causal attribution.
                        base = row["rolling_mean_6"]
                        if pd.notna(base):
                            out.loc[idx, "event_lift"] = (row["_interest"] - base) / (abs(base) + 1.0)

    # Cross-platform confirmation: optional table with title/date and engagement columns.
    out["cross_platform_confirmation_score"] = np.nan
    out["cross_platform_available"] = False
    if cross_platform is not None and not cross_platform.empty:
        cp = cross_platform.copy()
        cp_title = find_col(cp, TITLE_CANDIDATES)
        cp_date = find_col(cp, DATE_CANDIDATES)
        metric_cols = [c for c in cp.columns if any(k in norm(c) for k in
                       ["views", "engagement", "comments", "posts", "pageviews", "discussion", "likes"])]
        if cp_title and cp_date and metric_cols:
            cp["_title_key"] = cp[cp_title].astype(str).str.casefold().str.strip()
            cp["_date_key"] = pd.to_datetime(cp[cp_date], errors="coerce").dt.to_period("M").dt.to_timestamp()
            for c in metric_cols:
                cp[c] = safe_float(cp[c])
                cp[f"_growth_{c}"] = cp.groupby("_title_key")[c].pct_change()
            growth_cols = [f"_growth_{c}" for c in metric_cols]
            cp["_confirm"] = cp[growth_cols].clip(lower=-1, upper=5).mean(axis=1, skipna=True)
            cp_map = cp.groupby(["_title_key", "_date_key"])["_confirm"].mean()
            keys = pd.MultiIndex.from_arrays([
                out["_title"].astype(str).str.casefold().str.strip(),
                out["_date"].dt.to_period("M").dt.to_timestamp()
            ])
            vals = cp_map.reindex(keys).to_numpy()
            out["cross_platform_confirmation_score"] = vals
            out["cross_platform_available"] = pd.notna(vals)

    # Composite indicator is a transparent screening score, not probability of success.
    momentum_norm = out["search_momentum"].clip(-1, 3)
    consistency = out["trend_consistency"].clip(0, 1)
    volatility_penalty = out["volatility_cv_6"].clip(0, 5) / 5
    out["opportunity_screening_score"] = (
        0.45 * ((momentum_norm + 1) / 4).fillna(0.25)
        + 0.35 * consistency.fillna(0.25)
        + 0.20 * (1 - volatility_penalty).fillna(0.5)
    ) * 100
    out["prediction_reliability"] = np.select(
        [out["valid_observations_so_far"] < 6, out["valid_observations_so_far"] < 12,
         out["nonzero_observation_count_so_far"] < 4],
        ["low: under 6 observations", "limited: under 12 observations",
         "low: fewer than 4 non-zero observations"],
        default="eligible for evaluation; validate out-of-sample"
    )

    # Preserve original source columns plus engineered columns; helper columns are removed.
    helper_cols = ["_date", "_interest", "_title", "_state", "_category", "_month"]
    out = out.drop(columns=[c for c in helper_cols if c in out.columns])
    return out


def enrich_anime_metadata(anime_path, ratings_path=None):
    if not anime_path or not Path(anime_path).exists():
        return None
    anime = read_csv_flexible(anime_path)
    # Standardize useful metadata-derived features when available.
    if "genres" in anime.columns:
        anime["genre_count"] = anime["genres"].fillna("").astype(str).apply(
            lambda s: 0 if not s.strip() else len([v for v in s.split("|") if v.strip()])
        )
    elif "genre" in anime.columns:
        anime["genre_count"] = anime["genre"].fillna("").astype(str).apply(
            lambda s: 0 if not s.strip() else len([v for v in re.split(r"[,|]", s) if v.strip()])
        )
    for col in ["score", "rating", "members", "favorites", "scored_by", "popularity", "episodes", "year"]:
        if col in anime.columns:
            anime[col] = pd.to_numeric(anime[col], errors="coerce")
    if "members" in anime.columns and "favorites" in anime.columns:
        anime["favorites_per_member"] = anime["favorites"] / anime["members"].replace(0, np.nan)
    if "scored_by" in anime.columns and "members" in anime.columns:
        anime["rating_coverage"] = anime["scored_by"] / anime["members"].replace(0, np.nan)

    # IMDb ratings file is not anime-specific by itself. Keep it separate unless an IMDb title-ID
    # key exists in the anime file; never join unrelated IDs or assume titles match perfectly.
    if ratings_path and Path(ratings_path).exists():
        ratings = pd.read_csv(ratings_path, sep="\t", compression="gzip", low_memory=False)
        ratings["averageRating"] = pd.to_numeric(ratings["averageRating"], errors="coerce")
        ratings["numVotes"] = pd.to_numeric(ratings["numVotes"], errors="coerce")
        if "tconst" in anime.columns:
            anime = anime.merge(ratings, on="tconst", how="left")
    return anime


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--data-dir", default="./data", help="Folder containing source datasets")
    ap.add_argument("--output-dir", default="./outputs", help="Folder for generated CSV/report")
    ap.add_argument("--trends", default=None, help="Optional explicit Google Trends CSV path")
    ap.add_argument("--anime", default=None, help="Optional explicit anime metadata CSV path")
    ap.add_argument("--ratings", default=None, help="Optional IMDb title.ratings.tsv.gz path")
    ap.add_argument("--events", default=None, help="Optional events.csv with event_date and title")
    ap.add_argument("--cross-platform", default=None, help="Optional title/date plus views/comments/pageviews/etc CSV")
    ap.add_argument("--game-sales", default=None, help="Optional video game sales CSV or ZIP")
    args = ap.parse_args()

    data_dir, out_dir = Path(args.data_dir), Path(args.output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    def pick(explicit, patterns):
        if explicit:
            return Path(explicit)
        for pat in patterns:
            matches = sorted(data_dir.glob(pat))
            if matches:
                return matches[0]
        return None

    trends_path = pick(args.trends, ["time_series*.csv", "*trends*.csv", "*google*.csv"])
    anime_path = pick(args.anime, ["anime_dataset.csv", "anime.csv"])
    ratings_path = pick(args.ratings, ["title.ratings.tsv.gz", "title.ratings*.tsv.gz"])
    events_path = Path(args.events) if args.events else (data_dir / "events.csv")
    cp_path = Path(args.cross_platform) if args.cross_platform else (data_dir / "cross_platform.csv")
    game_path = pick(args.game_sales, ["vgsales.csv.zip", "vgsales.csv"])

    if not trends_path or not trends_path.exists():
        raise FileNotFoundError(f"No Google Trends CSV found in {data_dir}. Use --trends PATH.")

    trends = read_csv_flexible(trends_path)
    events = read_csv_flexible(events_path) if events_path.exists() else None
    cp = read_csv_flexible(cp_path) if cp_path.exists() else None
    engineered = engineer_trends(trends, events=events, cross_platform=cp)
    trend_out = out_dir / "safora_trend_features.csv"
    engineered.to_csv(trend_out, index=False)

    anime = enrich_anime_metadata(anime_path, ratings_path)
    anime_out = None
    if anime is not None:
        anime_out = out_dir / "safora_anime_metadata_features.csv"
        anime.to_csv(anime_out, index=False)

    games = load_game_sales(game_path) if game_path else None
    games_out = None
    if games is not None:
        games_out = out_dir / "video_game_sales_clean.csv"
        games.to_csv(games_out, index=False)

    date_col = find_col(trends, DATE_CANDIDATES)
    value_col = find_col(trends, VALUE_CANDIDATES)
    values = safe_float(trends[value_col]) if value_col else pd.Series(dtype=float)
    report = {
        "source_files": {
            "trends": str(trends_path),
            "anime_metadata": str(anime_path) if anime_path and anime_path.exists() else None,
            "imdb_ratings": str(ratings_path) if ratings_path and ratings_path.exists() else None,
            "events": str(events_path) if events_path.exists() else None,
            "cross_platform": str(cp_path) if cp_path.exists() else None,
            "video_game_sales": str(game_path) if game_path and game_path.exists() else None
        },
        "trends_rows": int(len(trends)),
        "trends_valid_numeric_values": int(values.notna().sum()),
        "trends_nonzero_values": int((values.fillna(0) > 0).sum()),
        "trends_unique_dates": int(pd.to_datetime(trends[date_col], errors="coerce").nunique()) if date_col else 0,
        "engineered_rows": int(len(engineered)),
        "features_written": [c for c in engineered.columns if c not in trends.columns],
        "feature_availability": {
            "momentum_consistency_volatility_spike_risk": "calculated from available trend series",
            "seasonal_lift": "calculated where historical same-month observations exist",
            "regional_concentration": "only calculated when state/region column exists and comparable values exist",
            "search_diversity": "only calculated when query/category column exists",
            "event_lift": "requires optional events.csv with event_date and optionally title",
            "cross_platform_confirmation": "requires optional cross_platform.csv with title/date and engagement metric columns",
            "absolute_search_volume": "not available from normalized Google Trends index"
        },
        "cautions": [
            "Google Trends indices are normalized relative interest, not absolute search counts.",
            "A one-off non-zero observation is not sufficient evidence of a breakout.",
            "Opportunity screening score is a transparent heuristic, not a calibrated probability.",
            "IMDb title ratings are not joined to anime records unless a matching IMDb tconst key exists.",
            "Video game sales are kept as a separate dataset unless a defensible title mapping is provided."
        ],
        "outputs": {
            "trend_features": str(trend_out),
            "anime_metadata_features": str(anime_out) if anime_out else None,
            "video_game_sales": str(games_out) if games_out else None
        }
    }
    report_path = out_dir / "safora_data_quality_report.json"
    report_path.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps(report, indent=2))
    print("\nDone. Review the data-quality report before using the scores for decisions.")


if __name__ == "__main__":
    main()
