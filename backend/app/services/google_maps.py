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


async def geocode_address(address: str) -> dict:
    if not GOOGLE_MAPS_API_KEY:
        return {"error": "Missing GOOGLE_MAPS_API_KEY"}

    url = "https://maps.googleapis.com/maps/api/geocode/json"
    params = {
        "address": address,
        "key": GOOGLE_MAPS_API_KEY,
    }

    async with httpx.AsyncClient() as client:
        response = await client.get(url, params=params)
        response.raise_for_status()
        data = response.json()

    if not data.get("results"):
        return {"error": "No matching address found", "status": data.get("status"), "raw": data}

    first_result = data["results"][0]
    geometry = first_result.get("geometry", {})
    location = geometry.get("location", {})

    return {
        "formatted_address": first_result.get("formatted_address"),
        "latitude": location.get("lat"),
        "longitude": location.get("lng"),
        "place_id": first_result.get("place_id"),
        "status": data.get("status"),
        "raw": data,
    }


async def route_distance_to_destination(
    origin_latitude: float,
    origin_longitude: float,
    destination_latitude: float,
    destination_longitude: float,
) -> dict:
    if not GOOGLE_MAPS_API_KEY:
        return {"error": "Missing GOOGLE_MAPS_API_KEY"}

    route_url = "https://routes.googleapis.com/directions/v2:computeRoutes"
    headers = {
        "Content-Type": "application/json",
        "X-Goog-Api-Key": GOOGLE_MAPS_API_KEY,
        "X-Goog-FieldMask": "routes.distanceMeters,routes.duration",
    }
    route_request = {
        "origin": {
            "location": {
                "latLng": {
                    "latitude": origin_latitude,
                    "longitude": origin_longitude,
                }
            }
        },
        "destination": {
            "location": {
                "latLng": {
                    "latitude": destination_latitude,
                    "longitude": destination_longitude,
                }
            }
        },
        "travelMode": "DRIVE",
        "routingPreference": "TRAFFIC_AWARE",
    }

    async with httpx.AsyncClient() as client:
        response = await client.post(route_url, headers=headers, json=route_request)
        response.raise_for_status()
        data = response.json()

    routes = data.get("routes", [])
    if not routes:
        return {"error": "No routes found", "raw": data}

    first_route = routes[0]
    distance_meters = first_route.get("distanceMeters", 0)
    duration = first_route.get("duration")
    distance_miles = round(distance_meters * 0.000621371, 2)

    return {
        "distance_meters": distance_meters,
        "distance_miles": distance_miles,
        "duration": duration,
        "raw": data,
    }
