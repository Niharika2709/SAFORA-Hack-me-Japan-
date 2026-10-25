SAFORA ALL-DIMENSIONS PREPROCESSED DATA PACKAGE
================================================

This package focuses on regional, language-format, gender, age, manga, music/J-Pop, anime, Google Trends, and gaming data.

DATA ACTUALLY AVAILABLE AND CLEANED
- Regional: Google Trends region scores for Japanese media + survey respondent counts by reported location.
- Demographics: age/gender/state and anime awareness/watcher status from the uploaded audience survey. Names are excluded.
- Language-format: subbed/dubbed/both survey preferences. No explicit language labels were supplied.
- Manga: survey responses about manga reading and manga/manhwa/manhua/novel preference. This is NOT a manga catalogue.
- Anime: cleaned catalogue variants and user-rating table.
- Google Trends: cleaned wide and long time series, with date and numeric interest fields.
- Gaming: cleaned video-game sales data extracted from the uploaded archive.

IMPORTANT DATA GAPS (NOT FABRICATED)
- J-Pop Spotify source is now specified by the user. `music_jpop/prepare_jpop_spotify.py` downloads and preprocesses the actual Hugging Face dataset into SAFORA's data/raw and data/processed folders. The real CSV bytes were not accessible to this packaging runtime, so the package does not pretend that the empty schema template contains music records. Run the script to generate the real cleaned dataset.
- No title-level manga catalogue was uploaded. An empty schema template is provided, clearly labelled TEMPLATE_ONLY. Current manga outputs are survey-only.
- No explicit preferred-language field (e.g. Hindi/Japanese/English) exists in the survey. Subbed/dubbed preference is not equivalent to language.
- The survey is a small self-reported sample and should not be interpreted as representative of the Indian population.
- Google Trends values are relative search-interest indices, not sales, streaming counts, or revenue.
- Some regional survey responses are city-like or inconsistently formatted; they are preserved as reported rather than guessed into state names.

Preprocessing
- Standardized column names; trimmed text; normalized blank/missing values.
- Parsed dates and numeric measures.
- Removed duplicate rows or duplicate entity IDs where appropriate.
- Kept missing observations as missing; no synthetic rows/values were invented.
- Generated long-form time series for query-based modelling.
- No train/test split, scaling, model training or feature selection has been performed; those are model-pipeline steps.
