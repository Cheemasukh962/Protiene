from pathlib import Path

from fastapi import FastAPI
from fastapi import HTTPException
from fastapi import Request
from fastapi import Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from pydantic import EmailStr

from backend.app.config import CORS_ALLOWED_ORIGINS
from backend.app.config import GOOGLE_MAPS_API_KEY
from backend.app.services.auth import authenticate_user
from backend.app.services.auth import clear_auth_cookie
from backend.app.services.auth import create_access_token
from backend.app.services.auth import get_current_user_from_request
from backend.app.services.auth import register_user
from backend.app.services.auth import set_auth_cookie
from backend.app.services.favorites import delete_favorite_for_guest
from backend.app.services.favorites import get_or_create_guest_profile
from backend.app.services.favorites import list_favorites_for_guest
from backend.app.services.favorites import star_item_for_guest
from backend.app.services.favorites import tracker_available_now_for_guest
from backend.app.services.favorites import tracker_schedule_for_guest
from backend.app.services.google_maps import (
    geocode_address,
    reverse_geocode,
    route_distance_to_destination,
)
from backend.app.services.recommendations import build_recommendations
from backend.app.services.user_favorites import delete_favorite_for_user
from backend.app.services.user_favorites import list_favorites_for_user
from backend.app.services.user_favorites import star_item_for_user
from backend.app.services.user_favorites import tracker_available_now_for_user
from backend.app.services.user_favorites import tracker_schedule_for_user


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
    origin_mode: str | None = None
    origin_latitude: float | None = None
    origin_longitude: float | None = None
    origin_text: str | None = None
    keyword: str = ""
    travel_mode: str = "walking"
    max_results: int = 5
    sort_mode: str = "protein"
    result_mode: str = "global"
    per_hall_limit: int = 5


class FavoriteStarRequest(BaseModel):
    item_name: str


class AuthRegisterRequest(BaseModel):
    email: EmailStr
    password: str


class AuthLoginRequest(BaseModel):
    email: EmailStr
    password: str


app = FastAPI(title="Protein Finder")
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")
app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
GUEST_COOKIE_NAME = "dprotein_guest_id"


async def resolve_guest_profile_id(request: Request, response: Response) -> str:
    existing_cookie = request.cookies.get(GUEST_COOKIE_NAME)
    guest_profile_id = await get_or_create_guest_profile(existing_cookie)

    if existing_cookie != guest_profile_id:
        response.set_cookie(
            key=GUEST_COOKIE_NAME,
            value=guest_profile_id,
            httponly=True,
            samesite="lax",
            secure=False,
            max_age=60 * 60 * 24 * 365,
        )
    return guest_profile_id


async def resolve_current_user(request: Request) -> dict:
    return await get_current_user_from_request(request)


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


@app.post("/auth/register")
async def auth_register(payload: AuthRegisterRequest) -> dict:
    try:
        user = await register_user(payload.email, payload.password)
    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error)) from error
    return user


@app.post("/auth/login")
async def auth_login(payload: AuthLoginRequest, response: Response) -> dict:
    user = await authenticate_user(payload.email, payload.password)
    if not user:
        raise HTTPException(status_code=401, detail="Invalid email or password")
    token = create_access_token(user["id"])
    set_auth_cookie(response, token)
    return {"ok": True, "email": user["email"]}


@app.get("/auth/me")
async def auth_me(request: Request) -> dict:
    user = await resolve_current_user(request)
    return {
        "id": user["id"],
        "email": user["email"],
        "is_active": user["is_active"],
    }


@app.post("/auth/logout")
def auth_logout(response: Response) -> dict:
    clear_auth_cookie(response)
    return {"ok": True}


@app.post("/api/favorites/star")
async def star_favorite_item(
    payload: FavoriteStarRequest,
    request: Request,
    response: Response,
) -> dict:
    guest_profile_id = await resolve_guest_profile_id(request, response)
    try:
        favorite = await star_item_for_guest(guest_profile_id, payload.item_name)
    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error)) from error

    return {"ok": True, "favorite": favorite}


@app.get("/api/favorites")
async def get_favorites(request: Request, response: Response) -> dict:
    guest_profile_id = await resolve_guest_profile_id(request, response)
    favorites = await list_favorites_for_guest(guest_profile_id)
    return {"favorites": favorites}


@app.delete("/api/favorites/{favorite_id}")
async def delete_favorite(favorite_id: int, request: Request, response: Response) -> dict:
    guest_profile_id = await resolve_guest_profile_id(request, response)
    deleted = await delete_favorite_for_guest(guest_profile_id, favorite_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Favorite not found")
    return {"ok": True}


@app.get("/api/tracker/available-now")
async def tracker_available_now(request: Request, response: Response) -> dict:
    guest_profile_id = await resolve_guest_profile_id(request, response)
    return await tracker_available_now_for_guest(guest_profile_id)


@app.get("/api/tracker/schedule")
async def tracker_schedule(request: Request, response: Response) -> dict:
    guest_profile_id = await resolve_guest_profile_id(request, response)
    return await tracker_schedule_for_guest(guest_profile_id)


@app.post("/api/user/favorites/star")
async def star_user_favorite_item(
    payload: FavoriteStarRequest,
    request: Request,
) -> dict:
    user = await resolve_current_user(request)
    try:
        favorite = await star_item_for_user(user["id"], payload.item_name)
    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error)) from error
    return {"ok": True, "favorite": favorite}


@app.get("/api/user/favorites")
async def get_user_favorites(request: Request) -> dict:
    user = await resolve_current_user(request)
    favorites = await list_favorites_for_user(user["id"])
    return {"favorites": favorites}


@app.delete("/api/user/favorites/{favorite_id}")
async def delete_user_favorite(favorite_id: int, request: Request) -> dict:
    user = await resolve_current_user(request)
    deleted = await delete_favorite_for_user(user["id"], favorite_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Favorite not found")
    return {"ok": True}


@app.get("/api/user/tracker/available-now")
async def user_tracker_available_now(request: Request) -> dict:
    user = await resolve_current_user(request)
    return await tracker_available_now_for_user(user["id"])


@app.get("/api/user/tracker/schedule")
async def user_tracker_schedule(request: Request) -> dict:
    user = await resolve_current_user(request)
    return await tracker_schedule_for_user(user["id"])
