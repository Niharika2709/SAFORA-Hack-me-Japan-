"""Reusable SAFORA analytics logic adapted from the original Streamlit prototype."""
from typing import Any
import numpy as np
import pandas as pd
from sklearn.linear_model import LinearRegression
from sklearn.metrics import mean_absolute_error, mean_squared_error


def make_demo_data() -> pd.DataFrame:
    """Synthetic demonstration data only; not real market research."""
    rng = np.random.default_rng(42)
    titles = ["Skybound Legends", "Neon Samurai", "Moonlit Bento", "Crimson Orbit", "Pixel Shogun", "Whispering Sakura", "Mecha Frontier", "The Last Yokai", "Midnight Ramen", "Paper Crane Days", "Dragon Circuit", "Summer in Kyoto", "Starfall Academy", "Echoes of Edo", "Ninja Next Door", "Blue Lanterns", "Cyber Ronin", "Garden of Spirits", "Tokyo Afterglow", "The Fox's Promise", "Parallel Tokyo", "Lantern Festival", "Iron Koi", "A Thousand Comets", "Tea House Stories", "Shadow Circuit", "Kitsune Code", "Ocean of Stars", "Maple Season", "Samurai Signals"]
    dates = pd.date_range(end=pd.Timestamp.today().normalize(), periods=12, freq="MS")
    rows = []
    for title in titles:
        base, growth = int(rng.integers(18, 75)), float(rng.normal(1.8, 2.5))
        category = str(rng.choice(["Anime", "Gaming", "Manga", "Music"]))
        language = str(rng.choice(["Hindi", "English", "Tamil", "Telugu", "Bengali", "Malayalam"]))
        region = str(rng.choice(["North", "South", "West", "East", "Central"]))
        rating = float(np.clip(rng.normal(7.2, .8), 4.5, 9.8))
        for i, date in enumerate(dates):
            interest = float(np.clip(base + growth * i + rng.normal(0, 8), 0, 100))
            reviews = int(max(0, interest * rng.uniform(10, 45) + rng.normal(0, 100)))
            engagement = float(np.clip(interest * .65 + rating * 4 + rng.normal(0, 10), 0, 100))
            rows.append({"title": title, "category": category, "month": date, "search_interest": round(interest, 2), "rating": round(rating, 2), "reviews": reviews, "engagement": round(engagement, 2), "language": language, "region": region})
    df = pd.DataFrame(rows)
    df.attrs["synthetic_demo"] = True
    return df


def prepare_data(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    df.columns = [str(c).strip().lower().replace(" ", "_") for c in df.columns]
    aliases = {"name":"title", "content":"title", "content_title":"title", "date":"month", "timestamp":"month", "google_trends":"search_interest", "trend":"search_interest", "score":"search_interest", "imdb_rating":"rating", "ratings":"rating", "review_count":"reviews", "engagement_score":"engagement", "type":"category", "genre":"category"}
    df = df.rename(columns={c: aliases[c] for c in df.columns if c in aliases})
    missing = [c for c in ["title", "search_interest"] if c not in df.columns]
    if missing:
        raise ValueError("CSV requires columns: title, search_interest. Missing: " + ", ".join(missing))
    if "month" not in df.columns:
        df["month"] = pd.Timestamp.today().normalize()
    defaults = {"rating":0, "reviews":0, "engagement":0, "category":"Unknown", "language":"Not specified", "region":"Not specified"}
    for col, default in defaults.items():
        if col not in df.columns: df[col] = default
    df["month"] = pd.to_datetime(df["month"], errors="coerce")
    for col in ["search_interest", "rating", "reviews", "engagement"]:
        df[col] = pd.to_numeric(df[col], errors="coerce")
    df = df.dropna(subset=["title", "month", "search_interest"])
    df["title"] = df["title"].astype(str).str.strip()
    df = df[df["title"] != ""]
    df["search_interest"] = df["search_interest"].clip(0, 100)
    for col in ["rating", "reviews", "engagement"]: df[col] = df[col].fillna(0)
    for col in ["category", "language", "region"]: df[col] = df[col].fillna("Unknown").astype(str)
    if df.empty: raise ValueError("No valid rows found. Check CSV dates and search-interest values.")
    return df.sort_values(["title", "month"]).reset_index(drop=True)


def _scale(s: pd.Series) -> pd.Series:
    s = pd.to_numeric(s, errors="coerce").fillna(0)
    lo, hi = float(s.min()), float(s.max())
    return pd.Series(50.0, index=s.index) if hi == lo else (s - lo) / (hi - lo) * 100


def score_titles(df: pd.DataFrame) -> pd.DataFrame:
    g = df.sort_values("month").groupby(["title", "category"], dropna=False).agg(
        avg_search=("search_interest", "mean"), latest_search=("search_interest", "last"), rating=("rating", "mean"), reviews=("reviews", "mean"), engagement=("engagement", "mean"), language=("language", "last"), region=("region", "last"), observations=("search_interest", "size")
    ).reset_index()
    weights = {"avg_search":.35, "latest_search":.25, "rating":.15, "reviews":.15, "engagement":.10}
    g["potential_score"] = sum(weights[c] * _scale(g[c]) for c in weights).round(1)
    g["potential"] = np.select([g["potential_score"] >= 70, g["potential_score"] >= 40], ["High", "Medium"], default="Low")
    return g.sort_values("potential_score", ascending=False).reset_index(drop=True)


def records(df: pd.DataFrame) -> list[dict[str, Any]]:
    out = df.copy()
    for c in out.columns:
        if pd.api.types.is_datetime64_any_dtype(out[c]): out[c] = out[c].dt.strftime("%Y-%m-%d")
    out = out.replace({np.nan: None, np.inf: None, -np.inf: None})
    return out.to_dict(orient="records")


def build_dashboard(df: pd.DataFrame, categories=None, start_date=None, end_date=None) -> dict[str, Any]:
    synthetic = bool(df.attrs.get("synthetic_demo", False))
    df = prepare_data(df)
    if categories is not None: df = df[df["category"].isin(categories)]
    if start_date: df = df[df["month"] >= pd.Timestamp(start_date)]
    if end_date: df = df[df["month"] < pd.Timestamp(end_date) + pd.Timedelta(days=1)]
    if df.empty: raise ValueError("No data matches these filters. Change the selected category or date range.")
    df.attrs["synthetic_demo"] = synthetic
    ranking = score_titles(df)
    trend = df.groupby("month", as_index=False)["search_interest"].mean().sort_values("month")
    mix = ranking["potential"].value_counts().reindex(["High", "Medium", "Low"], fill_value=0)
    tm = df.groupby(["title", "month"], as_index=False)["search_interest"].mean()
    months = sorted(tm["month"].unique())
    rising = []
    if len(months) >= 6:
        recent = tm[tm["month"].isin(months[-3:])].groupby("title")["search_interest"].mean().rename("recent_interest")
        prev = tm[tm["month"].isin(months[-6:-3])].groupby("title")["search_interest"].mean().rename("previous_interest")
        r = pd.concat([recent, prev], axis=1).dropna()
        r["change_points"] = (r["recent_interest"] - r["previous_interest"]).round(1)
        rising = records(r[r["change_points"] > 0].sort_values("change_points", ascending=False).reset_index().head(8))
    lang = df.groupby("language", as_index=False)["search_interest"].mean().sort_values("search_interest", ascending=False).round(1)
    region = df.groupby("region", as_index=False)["search_interest"].mean().sort_values("search_interest", ascending=False).round(1)
    return {"meta":{"synthetic_demo":synthetic,"rows":int(len(df)),"title_count":int(df.title.nunique()),"min_date":df.month.min().strftime("%Y-%m-%d"),"max_date":df.month.max().strftime("%Y-%m-%d"),"categories":sorted(df.category.astype(str).unique())},
            "kpis":{"titles_explored":int(df.title.nunique()),"average_interest":round(float(df.search_interest.mean()),1),"high_potential":int((ranking.potential=="High").sum()),"top_opportunity":str(ranking.iloc[0].title)},
            "monthly_trend":records(trend),"opportunity_mix":[{"name":str(k),"value":int(v)} for k,v in mix.items()],
            "ranking":records(ranking.round({"avg_search":1,"latest_search":1,"rating":1,"reviews":0,"engagement":1,"potential_score":1})),"rising_stars":rising,
            "language_signals":records(lang),"region_signals":records(region),"raw_titles":sorted(df.title.unique().tolist())}


def forecast_title(df: pd.DataFrame, title: str, horizon: int = 3) -> dict[str, Any]:
    df = prepare_data(df)
    one = df[df.title == title].sort_values("month").copy()
    if one.empty: raise ValueError("Title not found in the selected dataset.")
    one["time_index"] = np.arange(len(one))
    result = {"title":title,"history":records(one[["month","search_interest"]]),"mean_interest":round(float(one.search_interest.mean()),1),"latest_interest":round(float(one.iloc[-1].search_interest),1),"rating":round(float(one.rating.mean()),1) if one.rating.max()>0 else None,"forecast":[],"mae":None,"rmse":None,"note":"Illustrative linear baseline; not a guarantee of future demand."}
    if len(one) >= 5:
        split=max(3,int(len(one)*.8)); train,test=one.iloc[:split],one.iloc[split:]
        model=LinearRegression().fit(train[["time_index"]],train.search_interest)
        if len(test):
            pred=np.clip(model.predict(test[["time_index"]]),0,100)
            result["mae"]=round(float(mean_absolute_error(test.search_interest,pred)),2)
            result["rmse"]=round(float(np.sqrt(mean_squared_error(test.search_interest,pred))),2)
        idx=np.arange(len(one),len(one)+max(1,min(int(horizon),12)))
        vals=np.clip(model.predict(pd.DataFrame({"time_index":idx})),0,100)
        dates=pd.date_range(one.month.max()+pd.offsets.MonthBegin(1),periods=len(idx),freq="MS")
        result["forecast"]=[{"month":d.strftime("%Y-%m-%d"),"search_interest":round(float(v),1)} for d,v in zip(dates,vals)]
    result["history"]=[{"month":pd.Timestamp(r["month"]).strftime("%Y-%m-%d"),"search_interest":float(r["search_interest"])} for r in one[["month","search_interest"]].to_dict("records")]
    return result
