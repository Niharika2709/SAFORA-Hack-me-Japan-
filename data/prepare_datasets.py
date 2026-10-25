
from pathlib import Path
import zipfile
import pandas as pd

ROOT = Path(__file__).resolve().parent
DATA = ROOT
OUT = DATA / "processed"
OUT.mkdir(parents=True, exist_ok=True)


# 1. Clean anime catalogue and resolve duplicate IDs
anime = pd.read_csv(DATA / "anime_dataset.csv")
anime["mal_id"] = pd.to_numeric(anime["mal_id"], errors="coerce")
anime = anime.dropna(subset=["mal_id"]).copy()
anime["mal_id"] = anime["mal_id"].astype(int)

anime["_votes"] = pd.to_numeric(
    anime.get("scored_by", 0), errors="coerce"
)
anime["_score"] = pd.to_numeric(
    anime.get("score", 0), errors="coerce"
)
anime = anime.sort_values(
    ["_score", "_votes"], ascending=False, na_position="last"
)
anime = anime.drop_duplicates("mal_id", keep="first")
anime = anime.drop(columns=["_votes", "_score"])

# Supplementary legacy catalogue fields, matched by ID
legacy = pd.read_csv(DATA / "anime.csv")
legacy["anime_id"] = pd.to_numeric(legacy["anime_id"], errors="coerce")
legacy = legacy.dropna(subset=["anime_id"]).copy()
legacy["anime_id"] = legacy["anime_id"].astype(int)
legacy = legacy.drop_duplicates("anime_id")

legacy = legacy.rename(columns={
    "anime_id": "mal_id",
    "name": "legacy_name",
    "genre": "legacy_genre",
    "rating": "legacy_rating",
    "members": "legacy_members",
})

keep = [
    c for c in [
        "mal_id", "legacy_name", "legacy_genre",
        "legacy_rating", "legacy_members"
    ] if c in legacy.columns
]
anime = anime.merge(
    legacy[keep], on="mal_id", how="left", validate="one_to_one"
)
anime.to_csv(OUT / "anime_catalogue_clean.csv", index=False)
print("Anime catalogue:", len(anime), "unique IDs")

# 2. Clean Google Trends history
trends = pd.read_csv(DATA / "SAFORA_clean_monthly_trends.csv")
trends["date"] = pd.to_datetime(trends["date"], errors="coerce")
trends["interest"] = pd.to_numeric(trends["interest"], errors="coerce")
trends["query"] = trends["query"].astype("string").str.strip()
trends = trends.dropna(subset=["date", "interest", "query"]).copy()
trends = trends.drop_duplicates(["date", "query", "interest"])

if trends.duplicated(["date", "query"]).any():
    raise ValueError(
        "Conflicting values exist for a query/month. "
        "Resolve them before forecasting."
    )

trends = trends.sort_values(["query", "date"])
trends.to_csv(OUT / "google_trends_clean.csv", index=False)
print("Google Trends:", len(trends), "observations")

# 3. Clean game sales separately; not anime merchandise sales
with zipfile.ZipFile(DATA / "vgsales.csv.zip") as z:
    csv_name = next(
        n for n in z.namelist() if n.lower().endswith(".csv")
    )
    with z.open(csv_name) as f:
        games = pd.read_csv(f)

games["Year"] = pd.to_numeric(games["Year"], errors="coerce")
games["Global_Sales"] = pd.to_numeric(
    games["Global_Sales"], errors="coerce"
)
games = games.dropna(
    subset=["Name", "Year", "Genre", "Global_Sales"]
).drop_duplicates()
games["Year"] = games["Year"].astype(int)
games.to_csv(OUT / "video_game_sales_clean.csv", index=False)
print("Video-game sales:", len(games), "records")

# 4. Save a manifest of the prepared datasets
manifest = pd.DataFrame([
    {
        "dataset": "anime_catalogue_clean.csv",
        "rows": len(anime),
        "purpose": "Anime catalogue analytics"
    },
    {
        "dataset": "google_trends_clean.csv",
        "rows": len(trends),
        "purpose": "Relative search-interest forecasting"
    },
    {
        "dataset": "video_game_sales_clean.csv",
        "rows": len(games),
        "purpose": "Separate historical game-sales analysis"
    }
])
manifest.to_csv(OUT / "dataset_manifest.csv", index=False)

print("\nPreparation complete. Files saved in:", OUT)
