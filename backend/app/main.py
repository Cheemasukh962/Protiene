from pathlib import Path

from fastapi import FastAPI
from fastapi import HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from backend.app.services.google_maps import (
    geocode_address,
    reverse_geocode,
    route_distance_to_destination,
)


BASE_DIR = Path(__file__).resolve().parent
STATIC_DIR = BASE_DIR / "static"


class LocationCoordinates(BaseModel):
    latitude: float
    longitude: float


class UserTestingRequest(BaseModel):
    origin_mode: str
    food_query: str
    origin_latitude: float | None = None
    origin_longitude: float | None = None
    origin_text: str | None = None

app = FastAPI(title="Protein Finder")
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")

SILO_MARKET_LATITUDE = 38.53840121991231
SILO_MARKET_LONGITUDE = -121.75272790479623


@app.get("/api/health")
def health_check() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/")
def home() -> FileResponse:
    return FileResponse(STATIC_DIR / "index.html")


@app.post("/api/location")
def receive_location(location: LocationCoordinates) -> dict[str, float | str]:
    print(
        f"Received location: Latitude={location.latitude}, Longitude={location.longitude}",
        flush=True,
    )
    return {
        "message": "Location received successfully",
        "latitude": location.latitude,
        "longitude": location.longitude,
    }


@app.post("/api/location/reverse-geocode")
async def reverse_geocode_location(location: LocationCoordinates) -> dict:
    return await reverse_geocode(location.latitude, location.longitude)


@app.get("/api/test/silo-reverse-geocode")
async def test_silo_reverse_geocode() -> dict:
    result = await reverse_geocode(SILO_MARKET_LATITUDE, SILO_MARKET_LONGITUDE)
    print(result, flush=True)
    return result


@app.post("/api/routes/to-silo")
async def route_to_silo_from_user(location: LocationCoordinates) -> dict:
    result = await route_distance_to_destination(
        origin_latitude=location.latitude,
        origin_longitude=location.longitude,
        destination_latitude=SILO_MARKET_LATITUDE,
        destination_longitude=SILO_MARKET_LONGITUDE,
    )
    print(
        {
            "origin_latitude": location.latitude,
            "origin_longitude": location.longitude,
            "destination_name": "Silo Market",
            "destination_latitude": SILO_MARKET_LATITUDE,
            "destination_longitude": SILO_MARKET_LONGITUDE,
            "distance_miles": result.get("distance_miles"),
            "duration": result.get("duration"),
            "error": result.get("error"),
        },
        flush=True,
    )
    return result


@app.post("/api/user-testing")
async def user_testing_intake(request: UserTestingRequest) -> dict:
    origin_latitude = request.origin_latitude
    origin_longitude = request.origin_longitude
    origin_label = "current location"

    if request.origin_mode == "current":
        if origin_latitude is None or origin_longitude is None:
            raise HTTPException(
                status_code=400,
                detail="origin_latitude and origin_longitude are required for current mode",
            )
    elif request.origin_mode == "typed":
        if not request.origin_text:
            raise HTTPException(status_code=400, detail="origin_text is required for typed mode")
        geocode_result = await geocode_address(request.origin_text)
        if geocode_result.get("error"):
            raise HTTPException(status_code=400, detail=geocode_result["error"])
        origin_latitude = geocode_result.get("latitude")
        origin_longitude = geocode_result.get("longitude")
        origin_label = geocode_result.get("formatted_address") or request.origin_text
    else:
        raise HTTPException(status_code=400, detail="origin_mode must be 'current' or 'typed'")

    if origin_latitude is None or origin_longitude is None:
        raise HTTPException(status_code=400, detail="Could not determine origin coordinates")

    route_preview = await route_distance_to_destination(
        origin_latitude=origin_latitude,
        origin_longitude=origin_longitude,
        destination_latitude=SILO_MARKET_LATITUDE,
        destination_longitude=SILO_MARKET_LONGITUDE,
    )

    output = {
        "origin_mode": request.origin_mode,
        "origin_label": origin_label,
        "origin_latitude": origin_latitude,
        "origin_longitude": origin_longitude,
        "food_query": request.food_query,
        "route_preview_to_silo_miles": route_preview.get("distance_miles"),
        "route_preview_to_silo_duration": route_preview.get("duration"),
        "route_error": route_preview.get("error"),
    }
    print(output, flush=True)
    return output
