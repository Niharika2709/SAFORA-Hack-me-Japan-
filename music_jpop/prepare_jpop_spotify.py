"""
Download and preprocess the official SAFORA J-Pop music source.
Source: https://huggingface.co/datasets/sdy623/JPOP-Sampled-Spotify

Run from SAFORA project root:
    python scripts/prepare_jpop_spotify.py

Requires:
    python -m pip install datasets pandas
Outputs:
    data/raw/jpop_spotify_raw.csv
    data/processed/jpop_spotify_clean.csv
"""
from pathlib import Path
import pandas as pd
from datasets import load_dataset

ROOT = Path(__file__).resolve().parents[1]
RAW_DIR = ROOT / "data" / "raw"
PROCESSED_DIR = ROOT / "data" / "processed"
RAW_DIR.mkdir(parents=True, exist_ok=True)
PROCESSED_DIR.mkdir(parents=True, exist_ok=True)

DATASET_ID = "sdy623/JPOP-Sampled-Spotify"
EXPECTED = [
    "track_id", "name", "artist", "album", "release_year", "release_date",
    "release_date_precision", "disc_number", "track_number", "total_tracks",
    "explicit", "popularity", "external_id", "duration_ms", "preview_url",
    "play_count",
]

print(f"Downloading real music data from {DATASET_ID}...")
dataset = load_dataset(DATASET_ID, split="train")
df = dataset.to_pandas()
df.columns = [str(c).strip().lower() for c in df.columns]

missing = sorted(set(EXPECTED) - set(df.columns))
if missing:
    raise ValueError(f"Dataset schema changed; missing columns: {missing}")
if df.empty:
    raise ValueError("The source returned zero tracks; refusing to save empty music data.")

# Preserve source rows for reproducibility.
df.to_csv(RAW_DIR / "jpop_spotify_raw.csv", index=False, encoding="utf-8-sig")

clean = df.copy()
for c in ["track_id", "name", "artist", "album", "release_date",
          "release_date_precision", "external_id", "preview_url"]:
    clean[c] = clean[c].astype("string").str.strip()
    clean[c] = clean[c].replace("", pd.NA)

for c in ["release_year", "disc_number", "track_number", "total_tracks",
          "popularity", "duration_ms", "play_count"]:
    clean[c] = pd.to_numeric(clean[c], errors="coerce")

clean["explicit"] = clean["explicit"].astype("boolean")
clean["release_date"] = pd.to_datetime(
    clean["release_date"], errors="coerce"
).dt.strftime("%Y-%m-%d")
clean["release_year"] = clean["release_year"].fillna(
    pd.to_datetime(clean["release_date"], errors="coerce").dt.year
).astype("Int64")

# Validate ranges rather than clipping or inventing values.
clean.loc[~clean["popularity"].between(0, 100), "popularity"] = pd.NA
clean.loc[clean["duration_ms"] <= 0, "duration_ms"] = pd.NA
clean.loc[clean["play_count"] < 0, "play_count"] = pd.NA
clean = clean.drop_duplicates(subset=["track_id"], keep="first")
clean = clean[clean["track_id"].notna() & clean["name"].notna() & clean["artist"].notna()]
clean = clean.reset_index(drop=True)

if clean.empty:
    raise ValueError("No valid tracks remained after cleaning; output was not written.")

output = PROCESSED_DIR / "jpop_spotify_clean.csv"
clean.to_csv(output, index=False, encoding="utf-8-sig")
print("Source rows:", len(df))
print("Clean rows:", len(clean))
print("Unique artists:", clean["artist"].nunique())
print("Missing values by column:")
print(clean.isna().sum().to_string())
print("Saved:", output)
