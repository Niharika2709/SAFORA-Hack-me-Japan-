# SAFORA Advanced Feature Engineering

## What this package does
- Calculates rolling search momentum, trend consistency, volatility, robust spike score/risk, seasonal lift and an opportunity screening score.
- Calculates regional Gini only when multiple regional rows exist for a title/date.
- Calculates search diversity only when query-category data exists.
- Calculates event lift only when an `events.csv` file exists.
- Calculates cross-platform confirmation only when a `cross_platform.csv` file exists with title/date and engagement metrics.
- Creates useful metadata features from the anime dataset.
- Keeps IMDb ratings and video-game sales separate unless reliable title IDs/mapping are available.

## Install
```powershell
py -m pip install pandas numpy
```

## Folder setup
Put `safora_feature_engineering.py` beside a folder called `data` and place the source datasets inside `data`, or specify your paths.

## Run
```powershell
py safora_feature_engineering.py --data-dir .\data --output-dir .\outputs
```

For explicit paths:
```powershell
py safora_feature_engineering.py --trends .\data\time_series_IN_20211024-1307_20261024-1307.csv --anime .\data\anime_dataset.csv --ratings .\data\title.ratings.tsv.gz --game-sales .\data\vgsales.csv.zip --output-dir .\outputs
```

## Optional files for additional signals

### `events.csv`
Must include `event_date`; optionally include a `title` column whose values match the title/query series.

### `cross_platform.csv`
Must include a title/query column, a date/time column, and one or more numeric metrics with names such as `views`, `engagement`, `comments`, `posts`, `pageviews`, `discussion`, or `likes`. One row per title/month is a useful format.

## Important findings in the supplied raw data
The supplied Google Trends file has 61 monthly observations, but only 3 are non-zero (December 2025 = 100, June 2026 = 65, October 2026 = 4). It is one generic series named `titles and franchise`, not separate anime-title × state × month observations. This is too sparse to validate reliable per-anime forecasting or breakout prediction. Re-export Google Trends data for each target anime/franchise and each target Indian state/region, using consistent comparison settings and enough history.

Google Trends is a normalized relative-interest index, not absolute search counts. Do not interpret its values as search volumes or market size.

The generated `opportunity_screening_score` is a transparent heuristic for prioritization, not a calibrated probability of commercial success. Evaluate forecasts using chronological train/test splits before using them for decisions.
