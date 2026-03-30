# DProtein System Architecture (Current)

## Why This Exists

This file explains the current architecture and the `GET` vs `POST` API structure so a new developer can understand the system quickly.

## High-Level Architecture

- Client: static HTML + JavaScript pages (`/`, `/static/route.html`, `/static/recommendations.html`)
- API server: FastAPI (`backend/app/main.py`)
- Service layer:
  - Google integrations: `backend/app/services/google_maps.py`
  - Recommendation logic: `backend/app/services/recommendations.py`
  - Postgres data access: `backend/app/services/postgres_db.py`
- Database: PostgreSQL (`venues`, `menu_items`)

## Current Request Flow

1. User opens a static page in the browser.
2. Frontend gathers input (origin mode, coordinates or typed origin, keyword, travel mode).
3. Frontend sends JSON to backend with `fetch(...)`.
4. FastAPI endpoint validates request payload.
5. Backend service logic runs:
   - geocode and route calls to Google APIs
   - DB query in Postgres
   - recommendation ranking
6. Backend returns JSON response.
7. Frontend renders response on page.

## GET vs POST In This App

### GET (read-only, no request body needed)

- `GET /`
  - returns main HTML page
- `GET /api/health`
  - returns service status
- `GET /api/public-map-config`
  - returns public Google Maps JS key

Use `GET` when retrieving data without submitting a structured payload.

### POST (submit JSON payload for processing)

- `POST /api/location`
  - accepts coordinates payload
- `POST /api/location/reverse-geocode`
  - accepts coordinates and returns address info
- `POST /api/distance`
  - accepts origin/destination and returns miles/duration
- `POST /api/route`
  - accepts route request and returns polyline + turn steps
- `POST /api/recommendations`
  - accepts origin + keyword + travel mode and returns ranked food options

Use `POST` when sending user input that backend must validate and compute on.

## Recommendation Logic Ownership

- Frontend responsibilities:
  - collect user input
  - send API request
  - display recommendation cards
- Backend responsibilities:
  - request validation
  - origin resolution
  - Postgres keyword matching
  - Google route distance lookup
  - sorting by business rules

## Current Ranking Rule

- Primary sort: `distance_miles` ascending (closest first)
- Tie-break: `protein_grams` descending (higher protein first)

## Known Gaps (Next Work)

- Persist user search history and recommendation impressions.
- Add production data ingestion updates for campus menus.
- Add open-hours filtering and stale-data checks.
- Add deployment baseline (Docker/hosted environment, secrets, monitoring).
