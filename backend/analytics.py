
"""Reusable SAFORA analytics logic adapted from the original Streamlit prototype."""

from typing import Any
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.linear_model import LinearRegression
from sklearn.metrics import mean_absolute_error, mean_squared_error



def load_real_trends_data() -> pd.DataFrame:
    """Load and validate real Google Trends observations."""

    project_root = Path(__file__).resolve().parent.parent
    csv_path = (
        project_root
        / "data"
        / "processed"
        / "google_trends_clean.csv"
    )

    if not csv_path.exists():
        raise FileNotFoundError(
            f"Cleaned Google Trends dataset not found: {csv_path}"
        )

    trends = pd.read_csv(csv_path)

    required = {"date", "query", "interest"}
    missing = required - set(trends.columns)

    if missing:
        raise ValueError(
            f"Google Trends CSV is missing columns: {sorted(missing)}"
        )

    df = trends.rename(
        columns={
            "date": "month",
            "query": "title",
            "interest": "search_interest",
        }
    )

    df["month"] = pd.to_datetime(df["month"], errors="coerce")
    df["search_interest"] = pd.to_numeric(
        df["search_interest"], errors="coerce"
    )

    df = df.dropna(
        subset=["month", "title", "search_interest"]
    ).copy()

    df["title"] = df["title"].astype(str).str.strip()
    df = df[df["title"] != ""]

    if "category" not in df.columns:
        df["category"] = "Search Trends"

    # Do not invent ratings, reviews or engagement.
    # Use neutral defaults only for compatibility with existing code.
    for col in ["rating", "reviews", "engagement"]:
        if col not in df.columns:
            df[col] = 0.0
        else:
            df[col] = pd.to_numeric(df[col], errors="coerce")

    for col in ["language", "region"]:
        if col not in df.columns:
            df[col] = "Not specified"
        else:
            df[col] = (
                df[col]
                .fillna("Not specified")
                .astype(str)
                .str.strip()
                .replace("", "Not specified")
            )

    if df.empty:
        raise ValueError(
            "No valid Google Trends observations were found."
        )

    df = prepare_data(df)
    df.attrs["synthetic_demo"] = False

    return df


def load_real_trends_data() -> pd.DataFrame:
    """Load and validate real Google Trends observations."""
    project_root = Path(__file__).resolve().parent.parent
    csv_path = (
        project_root
        / "data"
        / "processed"
        / "google_trends_clean.csv"
    )

    if not csv_path.exists():
        raise FileNotFoundError(
            f"Cleaned Google Trends dataset not found: {csv_path}"
        )

    trends = pd.read_csv(csv_path)

    required = {"date", "query", "interest"}
    missing = required - set(trends.columns)
    if missing:
        raise ValueError(
            f"Google Trends CSV is missing columns: {sorted(missing)}"
        )

    df = trends.rename(
        columns={
            "date": "month",
            "query": "title",
            "interest": "search_interest",
        }
    ).copy()

    df["month"] = pd.to_datetime(df["month"], errors="coerce")
    df["search_interest"] = pd.to_numeric(
        df["search_interest"], errors="coerce"
    )

    df = df.dropna(
        subset=["month", "title", "search_interest"]
    ).copy()

    df["title"] = df["title"].astype(str).str.strip()
    df = df[df["title"] != ""]

    if "category" not in df.columns:
        df["category"] = "Search Trends"

    for col in ["rating", "reviews", "engagement"]:
        if col not in df.columns:
            df[col] = 0.0
        else:
            df[col] = pd.to_numeric(df[col], errors="coerce")

    for col in ["language", "region"]:
        if col not in df.columns:
            df[col] = "Not specified"
        else:
            df[col] = (
                df[col]
                .fillna("Not specified")
                .astype(str)
                .str.strip()
                .replace("", "Not specified")
            )

    if df.empty:
        raise ValueError("No valid Google Trends observations were found.")

    df = prepare_data(df)
    df.attrs["synthetic_demo"] = False
    return df


def prepare_data(df: pd.DataFrame) -> pd.DataFrame:
    """Normalize column names, types and missing values."""
    df = df.copy()
    df.columns = [
        str(column).strip().lower().replace(" ", "_")
        for column in df.columns
    ]

    aliases = {
        "name": "title",
        "content": "title",
        "content_title": "title",
        "date": "month",
        "timestamp": "month",
        "google_trends": "search_interest",
        "trend": "search_interest",
        "score": "search_interest",
        "imdb_rating": "rating",
        "ratings": "rating",
        "review_count": "reviews",
        "engagement_score": "engagement",
        "type": "category",
        "genre": "category",
    }

    df = df.rename(
        columns={column: aliases[column] for column in df.columns if column in aliases}
    )

    missing = [
        column
        for column in ["title", "search_interest"]
        if column not in df.columns
    ]
    if missing:
        raise ValueError(
            "CSV requires columns: title, search_interest. Missing: "
            + ", ".join(missing)
        )

    if "month" not in df.columns:
        df["month"] = pd.Timestamp.today().normalize()

    defaults = {
        "rating": 0,
        "reviews": 0,
        "engagement": 0,
        "category": "Unknown",
        "language": "Not specified",
        "region": "Not specified",
    }

    for column, default in defaults.items():
        if column not in df.columns:
            df[column] = default

    df["month"] = pd.to_datetime(df["month"], errors="coerce")

    for column in ["search_interest", "rating", "reviews", "engagement"]:
        df[column] = pd.to_numeric(df[column], errors="coerce")

    df = df.dropna(subset=["title", "month", "search_interest"])
    df["title"] = df["title"].astype(str).str.strip()
    df = df[df["title"] != ""]
    df["search_interest"] = df["search_interest"].clip(0, 100)

    for column in ["rating", "reviews", "engagement"]:
        df[column] = df[column].fillna(0)

    for column in ["category", "language", "region"]:
        df[column] = (
            df[column]
            .fillna("Not specified")
            .astype(str)
            .str.strip()
            .replace("", "Not specified")
        )

    if df.empty:
        raise ValueError(
            "No valid rows found. Check CSV dates and search-interest values."
        )

    return df.sort_values(["title", "month"]).reset_index(drop=True)


def _scale(series: pd.Series) -> pd.Series:
    series = pd.to_numeric(series, errors="coerce").fillna(0)
    low = float(series.min())
    high = float(series.max())

    if high == low:
        return pd.Series(50.0, index=series.index)

    return (series - low) / (high - low) * 100


def score_titles(df: pd.DataFrame) -> pd.DataFrame:
    """Calculate heuristic opportunity scores."""
    grouped = (
        df.sort_values("month")
        .groupby(["title", "category"], dropna=False)
        .agg(
            avg_search=("search_interest", "mean"),
            latest_search=("search_interest", "last"),
            rating=("rating", "mean"),
            reviews=("reviews", "mean"),
            engagement=("engagement", "mean"),
            language=("language", "last"),
            region=("region", "last"),
            observations=("search_interest", "size"),
        )
        .reset_index()
    )

    weights = {
        "avg_search": 0.35,
        "latest_search": 0.25,
        "rating": 0.15,
        "reviews": 0.15,
        "engagement": 0.10,
    }

    grouped["potential_score"] = sum(
        weights[column] * _scale(grouped[column])
        for column in weights
    ).round(1)

    grouped["potential"] = np.select(
        [
            grouped["potential_score"] >= 70,
            grouped["potential_score"] >= 40,
        ],
        ["High", "Medium"],
        default="Low",
    )

    return grouped.sort_values(
        "potential_score", ascending=False
    ).reset_index(drop=True)


def records(df: pd.DataFrame) -> list[dict[str, Any]]:
    """Convert a DataFrame into JSON-friendly records."""
    output = df.copy()

    for column in output.columns:
        if pd.api.types.is_datetime64_any_dtype(output[column]):
            output[column] = output[column].dt.strftime("%Y-%m-%d")

    output = output.replace({np.nan: None, np.inf: None, -np.inf: None})
    return output.to_dict(orient="records")


def build_dashboard(
    df: pd.DataFrame,
    categories=None,
    start_date=None,
    end_date=None,
) -> dict[str, Any]:
    """Build the dashboard response using the selected data and filters."""
    synthetic = bool(df.attrs.get("synthetic_demo", False))
    df = prepare_data(df)

    if categories is not None:
        df = df[df["category"].isin(categories)]

    if start_date:
        df = df[df["month"] >= pd.Timestamp(start_date)]

    if end_date:
        df = df[df["month"] < pd.Timestamp(end_date) + pd.Timedelta(days=1)]

    if df.empty:
        raise ValueError(
            "No data matches these filters. Change the selected category or date range."
        )

    df.attrs["synthetic_demo"] = synthetic
    ranking = score_titles(df)

    trend = (
        df.groupby("month", as_index=False)["search_interest"]
        .mean()
        .sort_values("month")
    )

    mix = ranking["potential"].value_counts().reindex(
        ["High", "Medium", "Low"], fill_value=0
    )

    title_month = df.groupby(
        ["title", "month"], as_index=False
    )["search_interest"].mean()

    months = sorted(title_month["month"].unique())
    rising = []

    if len(months) >= 6:
        recent = (
            title_month[title_month["month"].isin(months[-3:])]
            .groupby("title")["search_interest"]
            .mean()
            .rename("recent_interest")
        )
        previous = (
            title_month[title_month["month"].isin(months[-6:-3])]
            .groupby("title")["search_interest"]
            .mean()
            .rename("previous_interest")
        )

        changes = pd.concat([recent, previous], axis=1).dropna()
        changes["change_points"] = (
            changes["recent_interest"] - changes["previous_interest"]
        ).round(1)

        rising = records(
            changes[changes["change_points"] > 0]
            .sort_values("change_points", ascending=False)
            .reset_index()
            .head(8)
        )

    language = (
        df.groupby("language", as_index=False)["search_interest"]
        .mean()
        .sort_values("search_interest", ascending=False)
        .round(1)
    )

   
    # Load observed India regional Google Trends data.
    region_path = (
        Path(__file__).resolve().parent.parent
        / "data"
        / "processed"
        / "india_region_interest.csv"
    )

    if region_path.is_file():
        regional_df = pd.read_csv(region_path)

        if "region" not in regional_df.columns:
            raise ValueError(
                "Regional CSV must contain a 'region' column."
            )

        value_columns = [
            col for col in regional_df.columns if col != "region"
        ]

        if not value_columns:
            raise ValueError(
                "Regional CSV has no Google Trends interest column."
            )

        value_column = value_columns[0]
        region = regional_df[["region", value_column]].copy()
        region = region.rename(
            columns={value_column: "search_interest"}
        )
        region["search_interest"] = pd.to_numeric(
            region["search_interest"], errors="coerce"
        )
        region = region.dropna(
            subset=["region", "search_interest"]
        )
        region = region.sort_values(
            "search_interest", ascending=False
        ).round(1).reset_index(drop=True)
    else:
        region = pd.DataFrame(
            columns=["region", "search_interest"]
        )


    return {
        "meta": {
            "synthetic_demo": synthetic,
            "rows": int(len(df)),
            "title_count": int(df["title"].nunique()),
            "min_date": df["month"].min().strftime("%Y-%m-%d"),
            "max_date": df["month"].max().strftime("%Y-%m-%d"),
            "categories": sorted(df["category"].astype(str).unique()),
        },
        "kpis": {
            "titles_explored": int(df["title"].nunique()),
            "average_interest": round(float(df["search_interest"].mean()), 1),
            "high_potential": int((ranking["potential"] == "High").sum()),
            "top_opportunity": str(ranking.iloc[0]["title"]),
        },
        "monthly_trend": records(trend),
        "opportunity_mix": [
            {"name": str(name), "value": int(value)}
            for name, value in mix.items()
        ],
        "ranking": records(
            ranking.round(
                {
                    "avg_search": 1,
                    "latest_search": 1,
                    "rating": 1,
                    "reviews": 0,
                    "engagement": 1,
                    "potential_score": 1,
                }
            )
        ),
        "rising_stars": rising,
        "language_signals": records(language),
        "region_signals": records(region),
        "raw_titles": sorted(df["title"].unique().tolist()),
    }


def forecast_title(
    df: pd.DataFrame,
    title: str,
    horizon: int = 3,
) -> dict[str, Any]:
    """Produce an illustrative linear forecast for one title."""
    df = prepare_data(df)
    one = df[df["title"] == title].sort_values("month").copy()

    if one.empty:
        raise ValueError("Title not found in the selected dataset.")

    one["time_index"] = np.arange(len(one))

    result = {
        "title": title,
        "history": records(one[["month", "search_interest"]]),
        "mean_interest": round(float(one["search_interest"].mean()), 1),
        "latest_interest": round(float(one.iloc[-1]["search_interest"]), 1),
        "rating": (
            round(float(one["rating"].mean()), 1)
            if one["rating"].max() > 0
            else None
        ),
        "forecast": [],
        "mae": None,
        "rmse": None,
        "note": "Illustrative linear baseline; not a guarantee of future demand.",
    }

    if len(one) >= 5:
        split = max(3, int(len(one) * 0.8))
        train = one.iloc[:split]
        test = one.iloc[split:]

        model = LinearRegression().fit(
            train[["time_index"]], train["search_interest"]
        )

        if len(test):
            predictions = np.clip(
                model.predict(test[["time_index"]]), 0, 100
            )
            result["mae"] = round(
                float(mean_absolute_error(test["search_interest"], predictions)),
                2,
            )
            result["rmse"] = round(
                float(np.sqrt(mean_squared_error(test["search_interest"], predictions))),
                2,
            )

        indices = np.arange(
            len(one), len(one) + max(1, min(int(horizon), 12))
        )
        values = np.clip(
            model.predict(pd.DataFrame({"time_index": indices})), 0, 100
        )

        dates = pd.date_range(
            one["month"].max() + pd.offsets.MonthBegin(1),
            periods=len(indices),
            freq="MS",
        )

        result["forecast"] = [
            {
                "month": date.strftime("%Y-%m-%d"),
                "search_interest": round(float(value), 1),
            }
            for date, value in zip(dates, values)
        ]

    result["history"] = [
        {
            "month": pd.Timestamp(row["month"]).strftime("%Y-%m-%d"),
            "search_interest": float(row["search_interest"]),
        }
        for row in one[["month", "search_interest"]].to_dict("records")
    ]

    return result
