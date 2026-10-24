SAFORA — React + Vite frontend and FastAPI backend
==================================================
Requirements: Python 3.10+ and Node.js LTS (npm included).

PROJECT STRUCTURE
backend/main.py        FastAPI endpoints
backend/analytics.py   Reusable data cleaning, opportunity score, Rising Stars and forecast logic
backend/requirements.txt
frontend/               React + Vite website
frontend/src/App.jsx    Dashboard and interactions
frontend/src/styles.css Responsive cream/lavender/plum design

WINDOWS / VS CODE SETUP
1. Extract the ZIP, then open the extracted SAFORA_React_FastAPI folder in VS Code.
2. Open Terminal > New Terminal.

BACKEND TERMINAL (keep running):
   cd backend
   py -m venv .venv
   .\.venv\Scripts\python.exe -m pip install -r requirements.txt
   .\.venv\Scripts\python.exe -m uvicorn main:app --reload --host 127.0.0.1 --port 8000

FRONTEND: open a SECOND terminal (keep both terminals running):
   cd frontend
   npm install
   npm run dev

Open the URL printed by Vite, usually http://127.0.0.1:5173
API documentation: http://127.0.0.1:8000/docs

CSV FORMAT
Required columns: title, search_interest (numeric 0-100)
Optional: month, rating, reviews, engagement, category, language, region.
Common aliases like name/content, date/timestamp, score/trend, ratings, review_count, type/genre are normalized.

FEATURES
- Responsive React dashboard with collapsible plum sidebar and lavender/cream/sakura theme
- KPI cards, audience-interest area chart, opportunity donut chart
- Search/sort/export content ranking
- Category and date filters
- CSV upload to local FastAPI backend
- Rising Stars period comparison
- Language and region signals
- Linear regression baseline forecast with chronological holdout MAE/RMSE
- Methodology and limitations page

DATA HONESTY
Built-in data is synthetic demonstration data, not real Japanese market research. Uploaded CSV is kept in backend memory only and resets when the backend restarts; no database is configured. Forecasts are simple baselines, not guaranteed predictions.
Ports: frontend 5173, backend 8000.
