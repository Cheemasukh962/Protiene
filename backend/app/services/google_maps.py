import httpx

from backend.app.config import GOOGLE_MAPS_API_KEY


def _duration_text_to_seconds(duration_text: str | None) -> int | None:
    if not duration_text:
        return None

    # Routes API durations are typically formatted like "123s".
    raw_value = duration_text[:-1] if duration_text.endswith("s") else duration_text
    try:
        return int(raw_value)
    except ValueError:
        return None


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
    # Fallback candidates make short inputs like "Silo" resolve better near UC Davis.
    candidate_queries = [
        address.strip(),
        f"{address.strip()}, Davis, CA",
        f"{address.strip()}, UC Davis, CA",
    ]

    async with httpx.AsyncClient() as client:
        for candidate in candidate_queries:
            params = {
                "address": candidate,
                "key": GOOGLE_MAPS_API_KEY,
                "region": "us",
            }
            response = await client.get(url, params=params)
            response.raise_for_status()
            data = response.json()

            if data.get("results"):
                first_result = data["results"][0]
                geometry = first_result.get("geometry", {})
                location = geometry.get("location", {})
                return {
                    "formatted_address": first_result.get("formatted_address"),
                    "latitude": location.get("lat"),
                    "longitude": location.get("lng"),
                    "place_id": first_result.get("place_id"),
                    "status": data.get("status"),
                    "query_used": candidate,
                    "raw": data,
                }

    return {
        "error": "No matching address found. Try a more specific destination, like 'Silo Market Davis CA'.",
    }


async def route_distance_to_destination(
    origin_latitude: float,
    origin_longitude: float,
    destination_latitude: float,
    destination_longitude: float,
    travel_mode: str = "driving",
) -> dict:
    if not GOOGLE_MAPS_API_KEY:
        return {"error": "Missing GOOGLE_MAPS_API_KEY"}

    normalized_mode = travel_mode.strip().lower()
    google_travel_mode = "DRIVE"
    if normalized_mode in {"walk", "walking"}:
        google_travel_mode = "WALK"

    route_url = "https://routes.googleapis.com/directions/v2:computeRoutes"
    headers = {
        "Content-Type": "application/json",
        "X-Goog-Api-Key": GOOGLE_MAPS_API_KEY,
        "X-Goog-FieldMask": (
            "routes.distanceMeters,"
            "routes.duration,"
            "routes.polyline.encodedPolyline,"
            "routes.legs.steps.distanceMeters,"
            "routes.legs.steps.staticDuration,"
            "routes.legs.steps.navigationInstruction.instructions"
        ),
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
        "travelMode": google_travel_mode,
    }
    if google_travel_mode == "DRIVE":
        route_request["routingPreference"] = "TRAFFIC_AWARE"

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
    encoded_polyline = first_route.get("polyline", {}).get("encodedPolyline")
    first_leg = (first_route.get("legs") or [{}])[0]
    raw_steps = first_leg.get("steps", [])
    steps = []
    for index, step in enumerate(raw_steps, start=1):
        instruction = (
            step.get("navigationInstruction", {}).get("instructions")
            or "Continue"
        )
        step_distance_meters = step.get("distanceMeters", 0)
        step_distance_miles = round(step_distance_meters * 0.000621371, 2)
        step_duration_text = step.get("staticDuration")
        step_duration_seconds = _duration_text_to_seconds(step_duration_text)

        steps.append(
            {
                "step_number": index,
                "instruction_text": instruction,
                "distance_miles": step_distance_miles,
                "duration_seconds": step_duration_seconds,
                "duration_text": step_duration_text,
            }
        )

    return {
        "travel_mode": google_travel_mode,
        "distance_meters": distance_meters,
        "distance_miles": distance_miles,
        "duration": duration,
        "encoded_polyline": encoded_polyline,
        "steps": steps,
        "raw": data,
    }
