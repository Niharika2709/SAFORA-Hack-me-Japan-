from io import BytesIO
from threading import Lock
import pandas as pd
from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from analytics import make_demo_data, prepare_data, build_dashboard, forecast_title

app = FastAPI(title="SAFORA API", description="Japanese Media Market Intelligence local API", version="1.0.0")
app.add_middleware(CORSMiddleware, allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"], allow_credentials=True, allow_methods=["*"], allow_headers=["*"])
_lock = Lock()
_data = make_demo_data()

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
def reset_demo():
    global _data
    with _lock: _data=make_demo_data()
    return {"ok":True,"message":"Synthetic demo data restored."}
