# Protein Finder (DProtein) NEED JUST ONE HOUR PLEASE ALMSOT DONE WOKRING ON SETUP OF MY VERCEL IF NOT I WILL RECORD A VIDEO

Protein Finder is a FastAPI + React app focused on route distance and protein-aware food recommendations around UC Davis.

## Current Status

### Implemented

- Browser origin support:
  - current location (geolocation permission)
  - typed origin text (geocoded)
- Destination/place routing with Google APIs:
  - geocoding (`address/place text -> lat/lng`)
  - route distance and duration
  - driving and walking modes
  - encoded route polyline
  - turn-by-turn steps
- Recommendation MVP (`POST /api/recommendations`):
  - keyword input (example: `smoothie`)
  - Postgres-backed venue/menu lookup
  - ranking rule: closest distance first, then higher protein
  - backend service layer in `backend/app/services/recommendations.py`
- React frontend app (`frontend/`) with:
  - `/login` and `/signup` auth pages
  - `/` progressive location + search + results flow
  - `/route` route summary + turn-by-turn steps
- Legacy static pages still available under `backend/app/static/*` during migration.
- Tests:
  - `tests/test_distance.py`
  - `tests/test_recommendations.py`

### Not Finished Yet

- Persistent user history storage (searches, clicks, recommendations shown)
- Production data ingestion for real dining hall/menu updates
- Scraping or feed ingestion for UC Davis dining sources
- Hours/open-now filtering
- Production deployment + monitoring + key hardening

## Tech Stack

- Backend: `FastAPI`
- DB: `PostgreSQL` (`asyncpg`)
- Frontend: `React + TypeScript + Tailwind` (Vite)
- External APIs: Google Geocoding + Google Routes
- Tests: `pytest`

## API Endpoints

- `GET /api/health`
- `POST /api/location`
- `POST /api/location/reverse-geocode`
- `POST /api/distance`
- `POST /api/route`
- `POST /api/recommendations`
- `GET /api/public-map-config`

## Backend Logic Ownership

- Frontend (`recommendations.html`) only:
  - collects user input
  - calls `/api/recommendations`
  - renders returned cards/results
- Backend owns recommendation logic:
  - input validation
  - origin resolution (current vs typed)
  - keyword filtering from Postgres
  - route distance calls to Google Routes
  - ranking (distance first, protein second)

The `/api/recommendations` endpoint now delegates to:

- `backend/app/services/recommendations.py`

## Environment Variables

Create a `.env` file in the repo root:

```env
GOOGLE_MAPS_API_KEY=YOUR_GOOGLE_MAPS_KEY
POSTGRES_DSN=postgresql://postgres:YOUR_PASSWORD@localhost:5432/postgres
JWT_SECRET=CHANGE_ME_TO_A_LONG_RANDOM_SECRET
JWT_ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=60
COOKIE_NAME=dprotein_access_token
COOKIE_SECURE=false
COOKIE_SAMESITE=lax
CORS_ALLOWED_ORIGINS=http://localhost:8000,http://localhost:5173,http://127.0.0.1:8000,http://127.0.0.1:5173
```

## Run Locally (Backend)

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
uvicorn backend.app.main:app --reload
```

Open:

- `http://localhost:8000/`

## Run Locally (Frontend React)

```powershell
cd c:\Users\cheem\dprotein\frontend
cmd /c npm install
cmd /c npm run dev
```

Open:

- `http://localhost:5173`

The React app reads `VITE_API_BASE_URL` from `frontend/.env.local`.
Use:

```env
VITE_API_BASE_URL=http://localhost:8000
```

## Auth + Cookies + CORS

- Frontend API calls use `credentials: include` for HTTP-only cookie auth.
- Backend CORS must include frontend origin(s).
- `JWT_SECRET` is required for login/session endpoints (`/auth/login`, `/auth/me`, and `/api/user/*`).
- Use a single local host pattern for frontend + backend (`localhost` for both) to avoid cookie split issues.
- Default local origins now include:
  - `http://localhost:5173`
  - `http://127.0.0.1:5173`

## Railway + Vercel Deployment Env

Backend on Railway:

```env
POSTGRES_DSN=<Railway Postgres URL>
JWT_SECRET=<long random secret>
COOKIE_SECURE=true
COOKIE_SAMESITE=none
CORS_ALLOWED_ORIGINS=https://<your-vercel-domain>,http://localhost:5173
```

Frontend on Vercel:

```env
VITE_API_BASE_URL=https://<your-railway-backend-domain>
```

## PostgreSQL Notes

- Recommendation data currently uses seeded tables:
  - `venues`
  - `menu_items`
- Seed is created automatically on first recommendation query if tables are empty.
- Current build reads from Postgres for recommendations, but does **not** yet store user search history.

## Near-Term Roadmap

1. Add persistent logging tables for user searches and shown recommendations.
2. Build a menu data pipeline (manual admin import first, scraping second).
3. Add open-hours filtering and confidence metadata on each recommendation.
4. Deploy React frontend on Vercel and FastAPI + Postgres on Railway.
5. Add admin tools for editing venues/items without code changes.
