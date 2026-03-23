# Protein Finder

Protein Finder is a Python-first app for finding protein-friendly places and food options near a user.

## Current Architecture

- Backend: `FastAPI`
- Frontend: static `HTML + JavaScript`
- Python environment: local `.venv`
- Design rule:
  - Frontend handles browser permission, small input tasks, and display
  - Backend handles validation, API calls, ranking, and business logic

## Current Files

- Backend app: `backend/app/main.py`
- Frontend starter page: `backend/app/static/index.html`
- Dependencies: `requirements.txt`

## What Works Right Now

- `GET /` serves the starter page
- `GET /api/health` returns a health response
- `POST /api/location` accepts browser coordinates
- The browser can request the user location and send `latitude` and `longitude` to the backend

## Current Backend Flow

1. Browser requests geolocation permission
2. Frontend gets `latitude` and `longitude`
3. Frontend sends a `POST` request to `/api/location`
4. FastAPI validates the JSON using a Pydantic model
5. Backend returns JSON back to the page

## Run The Project

Start the server:

```powershell
.\.venv\Scripts\python.exe -m uvicorn backend.app.main:app --reload
```

Stop the server:

```powershell
Ctrl + C
```

Open in browser:

```text
http://127.0.0.1:8000/
```

## Key Learning Notes

- `@app.get(...)` and `@app.post(...)` create routes
- Pydantic models define and validate incoming JSON
- `print(...)` in Python shows in the terminal
- `console.log(...)` in JavaScript shows in the browser console
- `result.textContent = ...` updates the page

## Next Steps

1. Confirm the coordinate flow works end-to-end
2. Add simple backend logging for received coordinates
3. Set up environment variable support for API keys
4. Integrate Google Maps Platform from the backend
5. Start with reverse geocoding:
   - coordinates -> readable place/address
6. Then add nearby place search
7. Keep the frontend thin and move important logic into Python services/modules

## Planned Google Maps Usage

Most likely Google services to use next:

- Geocoding API
- Places API
- Maps JavaScript API

Recommended pattern:

1. Frontend gets browser coordinates
2. Frontend sends them to the backend
3. Backend calls Google APIs
4. Backend returns cleaned app-specific data
5. Frontend displays the result

## Good Prompt To Resume Later

```text
We are building Protein Finder with a Python-first backend using FastAPI. The frontend should stay thin. The app already has:
- GET /
- GET /api/health
- POST /api/location
and the frontend can request browser geolocation and POST latitude/longitude to the backend.

Next I want to integrate Google Maps Platform from the backend first, starting with reverse geocoding coordinates into a readable location. Please inspect the current files and continue from there.
```
