from datasets import load_dataset
from pathlib import Path

print("Downloading Anime Viewers dataset...")

ds = load_dataset("Mikey-TraceGod/Anime-Viewers-Data")

output_dir = Path("data/processed")
output_dir.mkdir(parents=True, exist_ok=True)

for split_name, dataset in ds.items():
    output_file = output_dir / f"anime_viewers_{split_name}.csv"
    dataset.to_csv(str(output_file), index=False)
    print(f"Saved: {output_file}")
    print(f"Rows: {len(dataset)}")
    print(f"Columns: {dataset.column_names}")

print("Download complete!")
