from math import atan2, cos, radians, sin, sqrt
from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from backend.app.services.google_maps import reverse_geocode, route_distance_to_destination


BASE_DIR = Path(__file__).resolve().parent
STATIC_DIR = BASE_DIR / "static"


class LocationCoordinates(BaseModel):
    latitude: float
    longitude: float


class CampusLocation(BaseModel):
    name: str
    latitude: float
    longitude: float
    category: str


class CampusLocationDistance(CampusLocation):
    distance_miles: float


CAMPUS_LOCATIONS = [
    CampusLocation(
        name="Silo",
        latitude=38.53830,
        longitude=-121.76168,
        category="Food and Beverage",
    ),
    CampusLocation(
        name="Segundo DC",
        latitude=38.54161,
        longitude=-121.75774,
        category="Dining Hall",
    ),
    CampusLocation(
        name="Memorial Union Market",
        latitude=38.54266,
        longitude=-121.74857,
        category="Market",
    ),
]

app = FastAPI(title="Protein Finder")
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")

SILO_MARKET_LATITUDE = 38.53840121991231
SILO_MARKET_LONGITUDE = -121.75272790479623


def calculate_distance_miles(
    lat1: float,
    lon1: float,
    lat2: float,
    lon2: float,
) -> float:
    earth_radius_miles = 3958.8

    lat1_rad = radians(lat1)
    lon1_rad = radians(lon1)
    lat2_rad = radians(lat2)
    lon2_rad = radians(lon2)

    dlat = lat2_rad - lat1_rad
    dlon = lon2_rad - lon1_rad

    a = sin(dlat / 2) ** 2 + cos(lat1_rad) * cos(lat2_rad) * sin(dlon / 2) ** 2
    c = 2 * atan2(sqrt(a), sqrt(1 - a))

    return earth_radius_miles * c


def build_location_distance(
    user_location: LocationCoordinates,
    campus_location: CampusLocation,
) -> CampusLocationDistance:
    distance_miles = calculate_distance_miles(
        user_location.latitude,
        user_location.longitude,
        campus_location.latitude,
        campus_location.longitude,
    )
    return CampusLocationDistance(**campus_location.model_dump(), distance_miles=distance_miles)


@app.get("/api/health")
def health_check() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/")
def home() -> FileResponse:
    return FileResponse(STATIC_DIR / "index.html")


@app.get("/api/campus_locations")
def get_campus_locations() -> list[CampusLocation]:
    return CAMPUS_LOCATIONS


@app.post("/api/campus/nearest")
def get_nearest_campus_location(
    location: LocationCoordinates,
) -> CampusLocationDistance:
    locations_with_distance = [
        build_location_distance(location, campus_location)
        for campus_location in CAMPUS_LOCATIONS
    ]
    return min(locations_with_distance, key=lambda campus_location: campus_location.distance_miles)


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
    silo = next(location for location in CAMPUS_LOCATIONS if location.name == "Silo")
    result = await reverse_geocode(silo.latitude, silo.longitude)
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
