from pathlib import Path
import pandas as pd
from datasets import load_dataset

ROOT = Path(__file__).resolve().parent
PROCESSED_DIR = ROOT / "data" / "processed"
PROCESSED_DIR.mkdir(parents=True, exist_ok=True)

print("Downloading J-Pop Spotify dataset...")

dataset = load_dataset("sdy623/JPOP-Sampled-Spotify")
print("Available splits:", list(dataset.keys()))

split_name = "train" if "train" in dataset else list(dataset.keys())[0]
df = dataset[split_name].to_pandas()

print("Downloaded rows:", len(df))
print("Columns:", df.columns.tolist())

output = PROCESSED_DIR / "jpop_spotify_clean.csv"
df.to_csv(output, index=False, encoding="utf-8-sig")

print("Saved successfully:", output)
print(df.head(5).to_string(index=False))
print("Music dataset preparation complete!")
