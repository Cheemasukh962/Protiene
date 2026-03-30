from typing import Any

from fastapi import HTTPException

from backend.app.services.google_maps import geocode_address
from backend.app.services.google_maps import route_distance_to_destination
from backend.app.services.postgres_db import search_keyword_top_item_per_venue


async def resolve_origin_coordinates(request: Any) -> tuple[float, float, str]:
    if request.origin_mode == "current":
        if request.origin_latitude is None or request.origin_longitude is None:
            raise HTTPException(
                status_code=400,
                detail="origin_latitude and origin_longitude are required for current mode",
            )
        return request.origin_latitude, request.origin_longitude, "Current location"

    if request.origin_mode == "typed":
        if not request.origin_text:
            raise HTTPException(status_code=400, detail="origin_text is required for typed mode")
        origin_geocode = await geocode_address(request.origin_text)
        if origin_geocode.get("error"):
            raise HTTPException(status_code=400, detail=origin_geocode["error"])
        origin_latitude = origin_geocode.get("latitude")
        origin_longitude = origin_geocode.get("longitude")
        if origin_latitude is None or origin_longitude is None:
            raise HTTPException(status_code=400, detail="Could not determine origin coordinates")
        origin_resolved = origin_geocode.get("formatted_address", "Typed origin")
        return origin_latitude, origin_longitude, origin_resolved

    raise HTTPException(status_code=400, detail="origin_mode must be 'current' or 'typed'")


async def build_recommendations(request: Any) -> dict:
    if request.max_results <= 0:
        raise HTTPException(status_code=400, detail="max_results must be greater than 0")

    keyword = request.keyword.strip()
    if not keyword:
        raise HTTPException(status_code=400, detail="keyword is required")

    origin_latitude, origin_longitude, origin_resolved = await resolve_origin_coordinates(request)

    try:
        matched_rows = await search_keyword_top_item_per_venue(keyword)
    except RuntimeError as error:
        raise HTTPException(status_code=503, detail=str(error)) from error

    if not matched_rows:
        return {
            "origin_resolved": origin_resolved,
            "keyword": keyword,
            "travel_mode": request.travel_mode,
            "recommendations": [],
            "message": "No matching protein options found.",
        }

    route_cache: dict[int, dict] = {}
    recommendations = []
    for row in matched_rows:
        venue_id = row["venue_id"]
        if venue_id not in route_cache:
            route_cache[venue_id] = await route_distance_to_destination(
                origin_latitude=origin_latitude,
                origin_longitude=origin_longitude,
                destination_latitude=row["venue_lat"],
                destination_longitude=row["venue_lng"],
                travel_mode=request.travel_mode,
            )

        route_result = route_cache[venue_id]
        recommendations.append(
            {
                "venue_id": venue_id,
                "venue_name": row["venue_name"],
                "venue_category": row["venue_category"],
                "item_name": row["item_name"],
                "protein_grams": row["protein_grams"],
                "tags": row["tags"],
                "distance_miles": route_result.get("distance_miles"),
                "duration": route_result.get("duration"),
                "why_selected": (
                    f"Matched keyword '{keyword}', ranked by closest distance then protein grams."
                ),
                "route_error": route_result.get("error"),
            }
        )

    recommendations.sort(
        key=lambda entry: (
            entry["distance_miles"] if entry["distance_miles"] is not None else float("inf"),
            -entry["protein_grams"],
        )
    )

    return {
        "origin_resolved": origin_resolved,
        "keyword": keyword,
        "travel_mode": request.travel_mode,
        "recommendations": recommendations[: request.max_results],
    }
