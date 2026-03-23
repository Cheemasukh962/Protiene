from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel


BASE_DIR = Path(__file__).resolve().parent
STATIC_DIR = BASE_DIR / "static"

app = FastAPI(title="Protein Finder")
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")


@app.get("/api/health")
def health_check() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/")
def home() -> FileResponse:
    return FileResponse(STATIC_DIR / "index.html")


class LocationCoordinates(BaseModel):
    latitude: float
    longitude: float


@app.post("/api/location")
def receive_location(location: LocationCoordinates) -> dict[str, float | str]:
    print(f"Received location: Latitude={location.latitude}, Longitude={location.longitude}")
    return {
        "message": "Location received successfully",
        "latitude": location.latitude,
        "longitude": location.longitude,
    }
