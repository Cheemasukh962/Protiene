from pathlib import Path

from fastapi import FastAPI
from fastapi import HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from backend.app.config import GOOGLE_MAPS_API_KEY
from backend.app.services.google_maps import (
    geocode_address,
    reverse_geocode,
    route_distance_to_destination,
)
from backend.app.services.recommendations import build_recommendations


BASE_DIR = Path(__file__).resolve().parent
STATIC_DIR = BASE_DIR / "static"


class LocationCoordinates(BaseModel):
    latitude: float
    longitude: float


class DistanceRequest(BaseModel):
    origin_mode: str
    origin_latitude: float | None = None
    origin_longitude: float | None = None
    origin_text: str | None = None
    destination_text: str
    travel_mode: str = "driving"


class RouteRequest(BaseModel):
    origin_mode: str
    origin_latitude: float | None = None
    origin_longitude: float | None = None
    origin_text: str | None = None
    destination_text: str
    travel_mode: str = "driving"


class RecommendationRequest(BaseModel):
    origin_mode: str
    origin_latitude: float | None = None
    origin_longitude: float | None = None
    origin_text: str | None = None
    keyword: str
    travel_mode: str = "walking"
    max_results: int = 5


app = FastAPI(title="Protein Finder")
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")


@app.get("/api/health")
def health_check() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/")
def home() -> FileResponse:
    return FileResponse(STATIC_DIR / "index.html")


@app.get("/api/public-map-config")
def public_map_config() -> dict[str, str]:
    return {"google_maps_js_api_key": GOOGLE_MAPS_API_KEY}


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


@app.post("/api/distance")
async def calculate_distance_to_destination(request: DistanceRequest) -> dict:
    if request.origin_mode == "current":
        if request.origin_latitude is None or request.origin_longitude is None:
            raise HTTPException(
                status_code=400,
                detail="origin_latitude and origin_longitude are required for current mode",
            )
        origin_latitude = request.origin_latitude
        origin_longitude = request.origin_longitude
        origin_resolved = "Current location"
    elif request.origin_mode == "typed":
        if not request.origin_text:
            raise HTTPException(status_code=400, detail="origin_text is required for typed mode")
        origin_geocode = await geocode_address(request.origin_text)
        if origin_geocode.get("error"):
            raise HTTPException(status_code=400, detail=origin_geocode["error"])
        origin_latitude = origin_geocode.get("latitude")
        origin_longitude = origin_geocode.get("longitude")
        origin_resolved = origin_geocode.get("formatted_address")
        if origin_latitude is None or origin_longitude is None:
            raise HTTPException(status_code=400, detail="Could not determine origin coordinates")
    else:
        raise HTTPException(status_code=400, detail="origin_mode must be 'current' or 'typed'")

    geocode_result = await geocode_address(request.destination_text)
    if geocode_result.get("error"):
        raise HTTPException(status_code=400, detail=geocode_result["error"])

    destination_latitude = geocode_result.get("latitude")
    destination_longitude = geocode_result.get("longitude")
    if destination_latitude is None or destination_longitude is None:
        raise HTTPException(status_code=400, detail="Could not determine destination coordinates")

    route_result = await route_distance_to_destination(
        origin_latitude=origin_latitude,
        origin_longitude=origin_longitude,
        destination_latitude=destination_latitude,
        destination_longitude=destination_longitude,
        travel_mode=request.travel_mode,
    )

    output = {
        "origin_mode": request.origin_mode,
        "origin_latitude": origin_latitude,
        "origin_longitude": origin_longitude,
        "origin_resolved": origin_resolved,
        "destination_text": request.destination_text,
        "destination_resolved": geocode_result.get("formatted_address"),
        "travel_mode": route_result.get("travel_mode"),
        "distance_miles": route_result.get("distance_miles"),
        "duration": route_result.get("duration"),
        "route_error": route_result.get("error"),
    }
    print(output, flush=True)
    return output


@app.post("/api/route")
async def calculate_route(request: RouteRequest) -> dict:
    if request.origin_mode == "current":
        if request.origin_latitude is None or request.origin_longitude is None:
            raise HTTPException(
                status_code=400,
                detail="origin_latitude and origin_longitude are required for current mode",
            )
        origin_latitude = request.origin_latitude
        origin_longitude = request.origin_longitude
        origin_resolved = "Current location"
    elif request.origin_mode == "typed":
        if not request.origin_text:
            raise HTTPException(status_code=400, detail="origin_text is required for typed mode")
        origin_geocode = await geocode_address(request.origin_text)
        if origin_geocode.get("error"):
            raise HTTPException(status_code=400, detail=origin_geocode["error"])
        origin_latitude = origin_geocode.get("latitude")
        origin_longitude = origin_geocode.get("longitude")
        origin_resolved = origin_geocode.get("formatted_address")
        if origin_latitude is None or origin_longitude is None:
            raise HTTPException(status_code=400, detail="Could not determine origin coordinates")
    else:
        raise HTTPException(status_code=400, detail="origin_mode must be 'current' or 'typed'")

    destination_geocode = await geocode_address(request.destination_text)
    if destination_geocode.get("error"):
        raise HTTPException(status_code=400, detail=destination_geocode["error"])

    destination_latitude = destination_geocode.get("latitude")
    destination_longitude = destination_geocode.get("longitude")
    if destination_latitude is None or destination_longitude is None:
        raise HTTPException(status_code=400, detail="Could not determine destination coordinates")

    route_result = await route_distance_to_destination(
        origin_latitude=origin_latitude,
        origin_longitude=origin_longitude,
        destination_latitude=destination_latitude,
        destination_longitude=destination_longitude,
        travel_mode=request.travel_mode,
    )

    output = {
        "origin_mode": request.origin_mode,
        "origin_resolved": origin_resolved,
        "destination_resolved": destination_geocode.get("formatted_address"),
        "travel_mode": route_result.get("travel_mode"),
        "distance_miles": route_result.get("distance_miles"),
        "duration": route_result.get("duration"),
        "encoded_polyline": route_result.get("encoded_polyline"),
        "steps": route_result.get("steps", []),
        "route_error": route_result.get("error"),
    }
    print(output, flush=True)
    return output


@app.post("/api/recommendations")
async def get_recommendations(request: RecommendationRequest) -> dict:
    return await build_recommendations(request)
