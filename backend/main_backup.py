
# ---------- REAL REGIONAL & ANIME TREND APIs ----------

from pathlib import Path
import pandas as pd
from fastapi import FastAPI, HTTPException


@app.get("/api/regional-analysis")
def regional_analysis():
    if not REGION_CSV.exists():
        raise HTTPException(status_code=404, detail=f"Regional dataset not found: {REGION_CSV}")

    try:
        df = pd.read_csv(REGION_CSV)

        if "region" not in df.columns or len(df.columns) < 2:
            raise ValueError("Expected region and interest columns.")

        interest_col = df.columns[1]
        df["interest"] = pd.to_numeric(df[interest_col], errors="coerce")
        df = df.dropna(subset=["region", "interest"]).copy()
        df["region"] = df["region"].astype(str).str.strip()
        df = df[df["region"] != ""]

        if df.empty:
            raise ValueError("No valid regional observations found.")

        df = df.sort_values("interest", ascending=False)

        regions = [
            {
                "region": str(row["region"]),
                "interest": round(float(row["interest"]), 1),
            }
            for _, row in df.iterrows()
        ]

        return {
            "source": "data/processed/india_region_interest.csv",
            "metric": str(interest_col),
            "metric_type": "Relative Google Trends interest (0-100)",
            "total_regions": len(regions),
            "regions": regions,
            "top_regions": regions[:10],
            "note": "Relative search interest over the source date range; not audience counts or market share.",
        }

    except Exception as exc:
        raise HTTPException(
            status_code=422,
            detail=f"Could not process regional dataset: {exc}",
        ) from exc


@app.get("/api/anime-trends")
def anime_trends():
    if not ANIME_TRENDS_CSV.exists():
        raise HTTPException(status_code=404, detail=f"Anime trends dataset not found: {ANIME_TRENDS_CSV}")

    try:
        df = pd.read_csv(ANIME_TRENDS_CSV)

        if "month" not in df.columns:
            raise ValueError("The anime trends CSV must contain a month column.")

        df["month"] = pd.to_datetime(df["month"], errors="coerce")
        df = df.dropna(subset=["month"]).sort_values("month")
        series = []

        for column in df.columns:
            if column == "month":
                continue

            values = pd.to_numeric(df[column], errors="coerce")
            valid = values.notna()

            if not valid.any():
                continue

            history = [
                {
                    "month": month.strftime("%Y-%m-%d"),
                    "interest": round(float(value), 1),
                }
                for month, value in zip(
                    df.loc[valid, "month"],
                    values[valid],
                )
            ]

            series.append({
                "title": str(column).replace(": (India)", ""),
                "source_column": str(column),
                "observations": int(valid.sum()),
                "nonzero_observations": int((values[valid] > 0).sum()),
                "latest_interest": history[-1]["interest"],
                "history": history,
            })

        if not series:
            raise ValueError("No usable anime trend series found.")

        return {
            "source": "data/processed/anime_trends.csv",
            "total_months": int(len(df)),
            "series": series,
            "note": "Google Trends relative interest, not absolute search volume. Historical trends do not guarantee future demand.",
        }

    except Exception as exc:
        raise HTTPException(
            status_code=422,
            detail=f"Could not process anime trends: {exc}",
        ) from exc

# ---------- END REGIONAL & ANIME TREND APIs ----------
