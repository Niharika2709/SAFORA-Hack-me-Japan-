from fastapi import FastAPI, File, HTTPException, UploadFile, Query
from pathlib import Path
from backend.analytics import (
    load_real_trends_data,
    prepare_data,
    build_dashboard,
    forecast_title,
)

from backend.music_analytics import (
    load_music_data,
    music_stats,
    list_music_tracks,
    top_music_tracks,
)
from io import BytesIO
from threading import Lock
import pandas as pd
from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
_data = load_real_trends_data()
_music_data = load_music_data()
app = FastAPI(title="SAFORA API", description="Japanese Media Market Intelligence local API", version="1.0.0")
app.add_middleware(CORSMiddleware, allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"], allow_credentials=True, allow_methods=["*"], allow_headers=["*"])
_lock = Lock()
class DashboardRequest(BaseModel):
    categories: list[str] | None = None
    start_date: str | None = None
    end_date: str | None = None

class ForecastRequest(BaseModel):
    title: str
    horizon: int = Field(default=3, ge=1, le=12)

def get_data():
    with _lock:
        d = _data.copy()
        d.attrs["synthetic_demo"] = bool(_data.attrs.get("synthetic_demo", False))
        return d

@app.get("/")
def root(): return {"app":"SAFORA API", "status":"ok", "docs":"/docs"}

@app.get("/api/health")
def health(): return {"status":"ok", "app":"SAFORA"}

@app.get("/api/options")
def options():
    d=get_data()
    return {"source":"synthetic demo" if d.attrs.get("synthetic_demo",False) else "uploaded CSV", "synthetic_demo":bool(d.attrs.get("synthetic_demo",False)), "categories":sorted(d.category.astype(str).unique().tolist()), "min_date":d.month.min().strftime("%Y-%m-%d"), "max_date":d.month.max().strftime("%Y-%m-%d"), "rows":len(d)}

@app.post("/api/dashboard")
def dashboard(req: DashboardRequest):
    try: return build_dashboard(get_data(), req.categories, req.start_date, req.end_date)
    except ValueError as e: raise HTTPException(status_code=422, detail=str(e)) from e

@app.post("/api/forecast")
def forecast(req: ForecastRequest):
    try: return forecast_title(get_data(), req.title, req.horizon)
    except ValueError as e: raise HTTPException(status_code=422, detail=str(e)) from e
@app.get("/api/music/stats")
def get_music_stats():
    return music_stats(_music_data)


@app.get("/api/music")
def get_music(
    limit: int = Query(default=100, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
    search: str | None = None,
    sort_by: str = "popularity",
):
    return list_music_tracks(
        _music_data,
        limit=limit,
        offset=offset,
        search=search,
        sort_by=sort_by,
    )


@app.get("/api/music/top")
def get_top_music(
    limit: int = Query(default=10, ge=1, le=100),
):
    return top_music_tracks(_music_data, limit=limit)
@app.post("/api/upload-csv")
async def upload_csv(file: UploadFile = File(...)):
    global _data
    if not file.filename or not file.filename.lower().endswith(".csv"): raise HTTPException(status_code=400, detail="Please upload a .csv file.")
    raw=await file.read()
    if len(raw)>20*1024*1024: raise HTTPException(status_code=413, detail="CSV is larger than 20 MB.")
    try: parsed=prepare_data(pd.read_csv(BytesIO(raw)))
    except Exception as e: raise HTTPException(status_code=422, detail=f"Could not parse CSV: {e}") from e
    parsed.attrs["synthetic_demo"]=False
    with _lock: _data=parsed
    return {"ok":True,"filename":file.filename,"rows":len(parsed),"titles":int(parsed.title.nunique()),"categories":sorted(parsed.category.astype(str).unique().tolist()),"message":"CSV loaded in server memory for this running session."}

@app.post("/api/reset-demo")
def reset_data():
    global _data

    refreshed = load_real_trends_data()

    with _lock:
        _data = refreshed

    return {
        "ok": True,
        "message": "Real trend data reloaded.",
        "synthetic_demo": bool(
            refreshed.attrs.get("synthetic_demo", False)
        ),
    }

@app.get("/api/audience-demographics")
def get_audience_demographics():
    """Return sample language, age and gender summaries."""
    csv_path = (
        Path(__file__).resolve().parent.parent
        / "data"
        / "processed"
        / "anime_watchers_dataset_10000.csv"
    )

    if not csv_path.is_file():
        raise HTTPException(
            status_code=404,
            detail=f"Audience dataset not found: {csv_path}",
        )

    try:
        df = pd.read_csv(csv_path)
    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail="Could not read the audience dataset.",
        ) from exc

    required = {"Age", "Gender", "Preferred_Language"}
    missing = required - set(df.columns)
    if missing:
        raise HTTPException(
            status_code=422,
            detail=f"Dataset is missing columns: {sorted(missing)}",
        )

    def distribution(column):
        values = df[column].dropna().astype(str).str.strip()
        values = values[values != ""]
        counts = values.value_counts()
        total = int(counts.sum())

        return [
            {
                "name": str(name),
                "count": int(count),
                "percentage": round(float(count) * 100 / total, 1),
            }
            for name, count in counts.items()
        ]

    age = pd.to_numeric(df["Age"], errors="coerce")
    age_groups = pd.cut(
        age,
        bins=[-float("inf"), 17, 24, 34, 44, 54, float("inf")],
        labels=[
            "17 and under",
            "18–24",
            "25–34",
            "35–44",
            "45–54",
            "55+",
        ],
    )
    age_counts = age_groups.value_counts(sort=False)
    valid_age_total = int(age_counts.sum())

    age_distribution = [
        {
            "name": str(group),
            "count": int(count),
            "percentage": round(float(count) * 100 / valid_age_total, 1)
            if valid_age_total else 0,
        }
        for group, count in age_counts.items()
    ]

    return {
        "source": "Mikey-TraceGod/Anime-Viewers-Data",
        "synthetic": True,
        "sample_size": int(len(df)),
        "language": distribution("Preferred_Language"),
        "age": age_distribution,
        "gender": distribution("Gender"),
        "note": (
            "Synthetic sample profiles for interface demonstration; "
            "not verified real-world audience demographics."
        ),
    }
