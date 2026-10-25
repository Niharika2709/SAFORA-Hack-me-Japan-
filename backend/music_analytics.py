
from pathlib import Path
import pandas as pd

BACKEND_DIR = Path(__file__).resolve().parent
PROJECT_DIR = BACKEND_DIR.parent

CSV_CANDIDATES = [
    PROJECT_DIR / "data" / "data" / "processed" / "jpop_spotify_clean.csv",
    PROJECT_DIR / "data" / "processed" / "jpop_spotify_clean.csv",
]


def load_music_data():
    csv_path = next((p for p in CSV_CANDIDATES if p.is_file()), None)
    if csv_path is None:
        raise FileNotFoundError(
            "J-Pop CSV not found. Checked: "
            + ", ".join(str(p) for p in CSV_CANDIDATES)
        )

    df = pd.read_csv(csv_path)
    required = [
        "track_id", "name", "artist", "album",
        "release_year", "release_date", "popularity",
        "duration_ms", "play_count",
    ]
    missing = [col for col in required if col not in df.columns]
    if missing:
        raise ValueError(f"J-Pop CSV missing columns: {missing}")

    df = df.copy()
    for col in ["name", "artist", "album", "track_id"]:
        df[col] = df[col].fillna("").astype(str).str.strip()

    for col in ["release_year", "popularity", "duration_ms", "play_count"]:
        df[col] = pd.to_numeric(df[col], errors="coerce")

    df = df[df["name"].ne("") & df["artist"].ne("")]
    df = df.drop_duplicates(subset=["track_id"], keep="first")
    return df.reset_index(drop=True)


def music_stats(df):
    plays = df["play_count"].dropna()
    popularity = df["popularity"].dropna()
    years = df["release_year"].dropna()

    return {
        "source": "real_jpop_spotify_csv",
        "rows": int(len(df)),
        "unique_tracks": int(df["track_id"].nunique()),
        "unique_artists": int(df["artist"].nunique()),
        "unique_albums": int(df.loc[df["album"].ne(""), "album"].nunique()),
        "average_popularity": round(float(popularity.mean()), 2) if len(popularity) else None,
        "total_play_count_in_dataset": int(plays.sum()) if len(plays) else None,
        "tracks_with_play_count": int(plays.count()),
        "min_release_year": int(years.min()) if len(years) else None,
        "max_release_year": int(years.max()) if len(years) else None,
    }


def list_music_tracks(df, limit=100, offset=0, search=None, sort_by="popularity"):
    allowed = {"popularity", "play_count", "release_year", "name", "artist"}
    if sort_by not in allowed:
        sort_by = "popularity"

    result = df.copy()
    if search:
        term = search.strip().casefold()
        mask = (
            result["name"].str.casefold().str.contains(term, regex=False)
            | result["artist"].str.casefold().str.contains(term, regex=False)
            | result["album"].str.casefold().str.contains(term, regex=False)
        )
        result = result[mask]

    result = result.sort_values(
        sort_by,
        ascending=sort_by in {"name", "artist", "release_year"},
        na_position="last",
    )
    total = len(result)
    result = result.iloc[offset:offset + limit]
    result = result.astype(object).where(pd.notna(result), None)

    return {
        "source": "real_jpop_spotify_csv",
        "total": int(total),
        "limit": int(limit),
        "offset": int(offset),
        "tracks": result.to_dict(orient="records"),
    }


def top_music_tracks(df, limit=10):
    result = df.sort_values(
        ["play_count", "popularity"],
        ascending=False,
        na_position="last",
    ).head(limit)
    result = result.astype(object).where(pd.notna(result), None)

    return {
        "source": "real_jpop_spotify_csv",
        "ranking_metric": "play_count",
        "tracks": result.to_dict(orient="records"),
    }
