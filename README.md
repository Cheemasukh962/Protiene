# DProtein : protiene.vercel.app

# VIDEO DEMO : https://youtu.be/wsZswz_mpjo


# FYI: You need your cookies enabled if you are in a private browser blokcing them it wont work


# Current Problem: IT TAKES A SECOND FOR A USER LOG IN TO REGISTER 
Works locally in terms of storing users sometimes has problems in vercel 

DProtein is a full-stack project to help UC Davis students quickly find high-protein food options nearby.
It combines location-aware ranking, route guidance, account auth, favorites, and a tracker view.

Backend is hosted on Railway (`FastAPI + PostgreSQL`) and frontend is hosted on Vercel (`React + Vite + Tailwind`).

## Project Goal

Build a practical recommendation app that demonstrates:

- Full-stack engineering (frontend + backend + database)
- Non-trivial backend logic (distance + protein ranking + day/meal filtering)
- External API integration (Google Maps APIs)
- System design thinking (guest/user split, persistence, deployment architecture)

## What It Does

- Accepts user location (current GPS or typed origin)
- Filters recommendations by meal and keyword
- Ranks results by closest distance first, then protein
- Shows route details (distance, ETA, steps, map polyline)
- Allows starring favorites
- Tracks favorite item availability by day/meal
- Supports both guest mode and signed-in user mode

## Tech Stack

- Backend: `FastAPI`
- Frontend: `React + TypeScript + Tailwind + Vite`
- Database: `PostgreSQL` (`asyncpg`)
- Auth: HTTP-only JWT cookies
- External APIs:
  - Google Geocoding / Reverse Geocoding
  - Google Routes
- Hosting:
  - Backend + Postgres: Railway
  - Frontend: Vercel

## High-Level Architecture

1. React frontend sends requests to FastAPI backend.
2. FastAPI handles business logic and DB queries.
3. FastAPI calls Google APIs for geocoding and route distance.
4. FastAPI returns ranked recommendations + route metadata.
5. Postgres stores user records, favorites, guest profiles, and dining item data.

## Recommendation Logic

Current recommendation flow (`POST /api/recommendations`):

1. Validate request fields:
  - `origin_mode`, `travel_mode`, `sort_mode`, `result_mode`, `meal_filter`, `day_override`
2. Resolve origin:
  - GPS coordinates (`current`) or geocode typed origin (`typed`)
3. Query Postgres dining rows (`public."TestData"`) with optional:
  - keyword filter
  - day filter
  - meal filter
4. If `sort_mode=closest`, call route API for each venue to get distance/duration.
5. Rank:
  - primary: smallest route distance
  - secondary: highest protein grams
6. Return top results + context fields (`applied_day`, `applied_meal`), calories, hours URL, and route metadata.

## Guest vs User Data Model

Guest mode and signed-in mode are intentionally separate.

- Guest mode:
  - Cookie: `dprotein_guest_id`
  - Tables: `guest_profiles`, `favorite_items`
  - Endpoints under `/api/favorites/*` and `/api/tracker/*`
- Signed-in mode:
  - Cookie: `dprotein_access_token` (JWT)
  - Tables: `users`, `user_favorite_items`
  - Endpoints under `/api/user/*`

This keeps guest data isolated from user-account data.

## Core Database Tables

- `public."TestData"`
  - dining hall rows used by recommendation + tracker logic
- `users`
  - email/password auth users
- `guest_profiles`
  - per-guest identity via cookie
- `favorite_items`
  - guest favorites
- `user_favorite_items`
  - user favorites

## API Endpoints

### Health and basic config

- `GET /api/health`
- `GET /api/public-map-config`

### Location and routing

- `POST /api/location`
- `POST /api/location/reverse-geocode`
- `POST /api/distance`
- `POST /api/route`

### Recommendations

- `POST /api/recommendations`

Supported request fields include:

- `origin_mode`: `current | typed`
- `origin_latitude`, `origin_longitude`, `origin_text`
- `meal_filter`: `Breakfast | Lunch | Dinner`
- `day_override`: weekday name
- `keyword`
- `travel_mode`: `walking | driving`
- `sort_mode`: `closest | protein`
- `result_mode`: `global | per_hall`

### Auth

- `POST /auth/register`
- `POST /auth/login`
- `GET /auth/me`
- `POST /auth/logout`

### Guest favorites and tracker

- `POST /api/favorites/star`
- `GET /api/favorites`
- `DELETE /api/favorites/{favorite_id}`
- `GET /api/tracker/available-now`
- `GET /api/tracker/schedule`
- `GET /api/tracker/overview`

### User favorites and tracker

- `POST /api/user/favorites/star`
- `GET /api/user/favorites`
- `DELETE /api/user/favorites/{favorite_id}`
- `GET /api/user/tracker/available-now`
- `GET /api/user/tracker/schedule`
- `GET /api/user/tracker/overview`

## Frontend Routes

- `/login`
- `/signup`
- `/`
- `/route`
- `/tracker`

Routing behavior:

- App defaults to login-first flow.
- User can explicitly continue as guest.
- Home/route/tracker are protected by auth or guest-mode gate.

## Local Setup

## 1) Backend

```powershell
cd c:\Users\cheem\dprotein
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
uvicorn backend.app.main:app --reload --host localhost --port 8000
```

## 2) Frontend

```powershell
cd c:\Users\cheem\dprotein\frontend
cmd /c npm install
cmd /c npm run dev
```

Local URLs:

- Frontend: `http://localhost:5173`
- Backend: `http://localhost:8000`

## Environment Variables

Root `.env`:

```env
GOOGLE_MAPS_API_KEY=YOUR_GOOGLE_MAPS_API_KEY
POSTGRES_DSN=postgresql://postgres:YOUR_PASSWORD@localhost:5432/postgres
JWT_SECRET=CHANGE_ME_TO_A_LONG_RANDOM_SECRET
JWT_ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=60
COOKIE_NAME=dprotein_access_token
COOKIE_SECURE=false
COOKIE_SAMESITE=lax
CORS_ALLOWED_ORIGINS=http://localhost:8000,http://localhost:5173,http://127.0.0.1:8000,http://127.0.0.1:5173
```

`frontend/.env.local`:

```env
VITE_API_BASE_URL=http://localhost:8000
```

## Railway + Vercel Deployment

## Railway (backend + DB)

1. Deploy backend service from branch `V3`.
2. Add Railway Postgres service.
3. In backend service variables, set:

```env
POSTGRES_DSN=${{ Postgres.DATABASE_URL }}
GOOGLE_MAPS_API_KEY=<your key>
JWT_SECRET=<long random secret>
JWT_ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=60
COOKIE_NAME=dprotein_access_token
COOKIE_SECURE=true
COOKIE_SAMESITE=none
CORS_ALLOWED_ORIGINS=https://<your-vercel-domain>,http://localhost:5173
```

4. Backend start command:

```bash
uvicorn backend.app.main:app --host 0.0.0.0 --port $PORT
```

5. Health check:

```text
https://<railway-backend-domain>/api/health
```

## Vercel (frontend)

1. Import same repo.
2. Root directory: `frontend`
3. Framework: `Vite`
4. Env:

```env
VITE_API_BASE_URL=https://<railway-backend-domain>
```

5. Deploy.

Note: `frontend/vercel.json` includes SPA rewrites so routes like `/login` and `/tracker` work directly.

## Importing Dining Data into Railway Postgres

Railway Postgres is separate from local Postgres, so data must be imported.

Typical flow:

1. Copy Railway Postgres public connection URL.
2. Import CSV into `public."TestData"` using `psql` or pgAdmin.
3. Verify row count:

```sql
SELECT COUNT(*) FROM public."TestData";
```

If `TestData` is empty, recommendation and tracker endpoints cannot return real menu results.

## Test and Verification Checklist

- `GET /api/health` returns OK
- Signup/login/logout works with cookie auth
- Home recommendations return ranked results
- Star toggling works from cards
- Tracker cards show favorite schedules
- Guest and user data remain separate
- Route page loads distance/directions
- Refresh keeps signed-in user session

## Railway + Vercel

This split was chosen for clarity and scalability:

- Railway: backend logic + persistent DB
- Vercel: fast frontend deployment and delivery


