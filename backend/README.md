# ABHEDYA VARAH — Backend starter

This is a FastAPI + SQLite starter for the uploaded single-file frontend.

## Important
Dashboard, weather, risk, infrastructure and historical endpoints currently return clearly marked **sample data**. They are not live disaster warnings and must not be presented as operational forecasts. Real provider integrations and model validation are a separate phase.

## Run on Windows / VS Code

Open this folder in VS Code. In the terminal:

```powershell
py -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
uvicorn main:app --reload
```

Open:
- API status: http://127.0.0.1:8000/api/health
- Interactive API docs: http://127.0.0.1:8000/docs

## Available endpoints

- `GET /api/health`
- `POST /api/auth/register`
- `POST /api/auth/login`
- `GET /api/auth/me` (Bearer token required)
- `GET /api/dashboard/summary`
- `GET /api/weather/current?lat=22.7196&lon=75.8577`
- `GET /api/risk?lat=22.7196&lon=75.8577`
- `GET /api/infrastructure`
- `GET /api/analytics/historical`
- `GET /api/alerts`
- `POST /api/alerts` (Bearer token required)
- `PATCH /api/alerts/{id}/resolve` (Bearer token required)

## Next integration step
Configure the frontend to call these endpoints using `fetch()` and a backend base URL. The current `index.html` does not yet contain these API calls. Then replace sample data adapters with live weather, verified sensor and official alert sources.

Before deployment: set a strong `JWT_SECRET`, restrict CORS to your frontend origin, use HTTPS, and add rate limiting, logging, database backups and security review. SQLite is suitable for a local demo; PostgreSQL/PostGIS is the likely next step for multi-user deployment and spatial queries.
