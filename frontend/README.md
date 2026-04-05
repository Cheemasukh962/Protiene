# DProtein Frontend (React)

This folder contains the React frontend for DProtein.

## Stack

- Vite
- React + TypeScript
- Tailwind CSS
- React Router

## Environment

Create `frontend/.env.local`:

```env
VITE_API_BASE_URL=http://localhost:8000
```

## Local Run

```powershell
cd c:\Users\cheem\dprotein\frontend
cmd /c npm install
cmd /c npm run dev
```

Open:

- `http://localhost:5173`

## Available Routes

- `/login`
- `/signup`
- `/`
- `/route`

## Backend Requirements

The FastAPI backend must be running with cookie auth enabled and CORS including your frontend origin.
Use the same host family locally for both apps (`localhost` + `localhost`) to keep cookies stable.

Local backend command:

```powershell
cd c:\Users\cheem\dprotein
.\.venv\Scripts\Activate.ps1
uvicorn backend.app.main:app --reload
```
