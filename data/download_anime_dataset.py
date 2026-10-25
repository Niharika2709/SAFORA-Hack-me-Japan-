
from datasets import load_dataset
from pathlib import Path

# Load the dataset from Hugging Face
ds = load_dataset("Mikey-TraceGod/Anime-Viewers-Data")

# Create an output folder
output_dir = Path("data/processed")
output_dir.mkdir(parents=True, exist_ok=True)

# Export each dataset split to CSV
for split_name, dataset in ds.items():
    output_file = output_dir / f"anime_viewers_{split_name}.csv"
    dataset.to_csv(str(output_file), index=False)
    print(f"Saved: {output_file}")
    print(f"Rows: {len(dataset)}")
    print(f"Columns: {dataset.column_names}")

print("Dataset download and CSV export complete.")
