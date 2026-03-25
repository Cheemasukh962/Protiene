import httpx

from backend.app.config import GOOGLE_MAPS_API_KEY


async def reverse_geocode(latitude: float, longitude: float) -> dict:
    if not GOOGLE_MAPS_API_KEY:
        return {"error": "Missing GOOGLE_MAPS_API_KEY"}

    url = "https://maps.googleapis.com/maps/api/geocode/json"
    params = {
        "latlng": f"{latitude},{longitude}",
        "key": GOOGLE_MAPS_API_KEY,
    }

    async with httpx.AsyncClient() as client:
        response = await client.get(url, params=params)
        response.raise_for_status()
        data = response.json()

    if not data.get("results"):
        return {
            "formatted_address": None,
            "place_id": None,
            "status": data.get("status"),
            "raw": data,
        }

    first_result = data["results"][0]

    return {
        "formatted_address": first_result.get("formatted_address"),
        "place_id": first_result.get("place_id"),
        "status": data.get("status"),
        "raw": data,
    }
