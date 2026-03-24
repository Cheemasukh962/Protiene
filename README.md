# Protein Finder

Protein Finder is a Python-first app for finding protein-friendly places and food options near a user.

## Project Direction

This project is being built with a backend-first mindset:

- Frontend stays thin
- Backend owns validation, external API calls, ranking, and business logic
- Features should be built in a way that shows system design thinking, not just UI work

The near-term goal is to:

1. Request the user's browser coordinates
2. Compare those coordinates against predetermined campus eating locations
3. Return the nearest matching location from the backend
4. Later add Google Maps APIs for reverse geocoding, typed location search, and map display

## Current Architecture

- Backend: `FastAPI`
- Frontend: static `HTML + JavaScript`
- Python environment: local `.venv`
- Testing: `pytest`

## Current Files

- Backend app: `backend/app/main.py`
- Frontend starter page: `backend/app/static/index.html`
- Tests: `tests/test_distance.py`
- Dependencies: `requirements.txt`

## What Works Right Now

- `GET /` serves the starter page
- `GET /api/health` returns a health response
- `POST /api/location` accepts browser coordinates
- `GET /api/campus_locations` returns a list of predetermined campus food locations
- `POST /api/campus/nearest` returns the nearest campus location based on user coordinates
- The backend can calculate distance between two coordinate points using the Haversine formula
- Automated tests cover both the distance helper and the nearest-location endpoint

## What We Added In This Session

We moved from basic geolocation capture into backend location logic.

### Backend improvements

- Added a `CampusLocation` model
- Added a `CampusLocationDistance` model
- Added a small in-memory campus dataset:
  - `Silo`
  - `Segundo DC`
  - `Memorial Union Market`
- Added `calculate_distance_miles(...)` using the Haversine formula
- Added `build_location_distance(...)` helper
- Added `POST /api/campus/nearest` to return the closest campus location

### Testing improvements

- Added a `tests/` folder
- Added `tests/test_distance.py`
- Added `pytest` to `requirements.txt`
- Added tests for:
  - same coordinates returning zero distance
  - symmetric distance behavior
  - positive distance for different coordinates
  - nearest campus location API behavior

## Current Backend Flow

1. Browser requests geolocation permission
2. Frontend gets `latitude` and `longitude`
3. Frontend can send coordinates to the backend
4. FastAPI validates the JSON using a Pydantic model
5. Backend can compare the user location against campus food locations
6. Backend returns the nearest location as JSON

## Distance Logic

The current project uses the Haversine formula to compare two latitude/longitude points on Earth.

Why this was chosen:

- Good for nearest-location comparison
- Simple and correct for MVP distance checks
- Better fit than Dijkstra's algorithm for this stage

Dijkstra's algorithm would only make sense later if the app models actual campus walking paths or route networks.

## Run The Project

Create the virtual environment:

```powershell
python -m venv .venv
```

Activate it:

```powershell
.\.venv\Scripts\Activate.ps1
```

Install dependencies:

```powershell
pip install -r requirements.txt
```

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

## Run Tests

Run the distance and API tests:

```powershell
.\.venv\Scripts\python.exe -m pytest tests/test_distance.py
```

Expected result right now:

- 4 tests passing

## Setup On Another Computer

To continue this project on another computer:

1. Clone or copy the project folder
2. Open the project in your editor
3. Create a virtual environment:

```powershell
python -m venv .venv
```

4. Activate it:

```powershell
.\.venv\Scripts\Activate.ps1
```

5. Install dependencies:

```powershell
pip install -r requirements.txt
```

6. Start the server:

```powershell
.\.venv\Scripts\python.exe -m uvicorn backend.app.main:app --reload
```

7. Run tests:

```powershell
.\.venv\Scripts\python.exe -m pytest tests/test_distance.py
```

## Next Steps

The next recommended steps are:

1. Update the frontend to call `POST /api/campus/nearest`
2. Show the nearest campus dining location on the page
3. Add more campus food locations to the backend dataset
4. Return the top 3 nearest locations instead of only one
5. Add reverse geocoding from Google Maps API
6. Add typed location search
7. Later add actual map rendering

## Recommended Next Coding Milestone

The best next milestone is:

- user clicks `Use my location`
- frontend sends coordinates to `POST /api/campus/nearest`
- backend returns the closest campus food location
- frontend displays the result cleanly

If that works, the app has a real backend-driven location feature before Google Maps is added.

## Good Prompt To Resume Later

```text
We are building Protein Finder with a Python-first FastAPI backend and a thin frontend. The app already supports browser geolocation, a campus location dataset, Haversine distance calculation, and a POST /api/campus/nearest route that returns the closest campus food location. Tests exist in tests/test_distance.py and currently pass. Next I want to connect the frontend to /api/campus/nearest and then continue toward Google Maps integration from the backend first.
```
