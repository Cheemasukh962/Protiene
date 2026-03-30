# Protein Finder (DProtein)

Protein Finder is a Python-first FastAPI app focused on backend logic for route distance and protein-aware food recommendations around UC Davis.

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
- Frontend pages:
  - `/` distance tester
  - `/static/route.html` route map + directions
  - `/static/recommendations.html` keyword recommendations
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
- Frontend: static `HTML + JS`
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

## Environment Variables

Create a `.env` file in the repo root:

```env
GOOGLE_MAPS_API_KEY=YOUR_GOOGLE_MAPS_KEY
POSTGRES_DSN=postgresql://postgres:YOUR_PASSWORD@localhost:5432/dprotein
```

## Run Locally

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
uvicorn backend.app.main:app --reload
```

Open:

- `http://127.0.0.1:8000/`

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
4. Add deployment baseline (Render/Fly/Railway), secrets, and health checks.
5. Add admin tools for editing venues/items without code changes.
