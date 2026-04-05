from typing import Any

from fastapi import HTTPException

from backend.app.services.day_filters import normalize_day_override
from backend.app.services.day_filters import resolve_applied_day
from backend.app.services.google_maps import geocode_address
from backend.app.services.google_maps import route_distance_to_destination
from backend.app.services.postgres_db import search_keyword_top_item_per_venue


def diversify_closest_global(recommendations: list[dict], max_results: int) -> list[dict]:
    """
    Make closest-mode global results easier to compare by hall.
    Pass 1 takes one best item per hall (nearest hall first), then pass 2 fills leftovers.
    """
    if max_results <= 0:
        return []

    grouped_by_venue: dict[str, list[dict]] = {}
    for recommendation in recommendations:
        grouped_by_venue.setdefault(recommendation["venue_id"], []).append(recommendation)

    for venue_items in grouped_by_venue.values():
        venue_items.sort(
            key=lambda entry: (
                entry["distance_miles"] if entry["distance_miles"] is not None else float("inf"),
                -entry["protein_grams"],
            )
        )

    venue_order = sorted(
        grouped_by_venue.keys(),
        key=lambda venue_id: (
            grouped_by_venue[venue_id][0]["distance_miles"]
            if grouped_by_venue[venue_id][0]["distance_miles"] is not None
            else float("inf"),
            -grouped_by_venue[venue_id][0]["protein_grams"],
        ),
    )

    diversified: list[dict] = []
    pointers: dict[str, int] = {venue_id: 0 for venue_id in venue_order}

    # First round: one per venue.
    for venue_id in venue_order:
        if len(diversified) >= max_results:
            break
        diversified.append(grouped_by_venue[venue_id][0])
        pointers[venue_id] = 1

    # Next rounds: fill remaining slots venue-by-venue in same closest order.
    while len(diversified) < max_results:
        added_any = False
        for venue_id in venue_order:
            index = pointers[venue_id]
            venue_items = grouped_by_venue[venue_id]
            if index < len(venue_items):
                diversified.append(venue_items[index])
                pointers[venue_id] = index + 1
                added_any = True
                if len(diversified) >= max_results:
                    break
        if not added_any:
            break

    return diversified


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

    # sort_mode controls ranking behavior:
    # - protein: highest protein first
    # - closest: nearest distance first, then protein
    sort_mode = getattr(request, "sort_mode", "protein")
    # result_mode controls response shape:
    # - global: one top list
    # - per_hall: grouped by dining hall
    result_mode = getattr(request, "result_mode", "global")
    per_hall_limit = int(getattr(request, "per_hall_limit", 5))

    if sort_mode not in {"protein", "closest"}:
        raise HTTPException(status_code=400, detail="sort_mode must be 'protein' or 'closest'")
    if result_mode not in {"global", "per_hall"}:
        raise HTTPException(status_code=400, detail="result_mode must be 'global' or 'per_hall'")
    if per_hall_limit not in {5, 10}:
        raise HTTPException(status_code=400, detail="per_hall_limit must be 5 or 10")

    keyword = request.keyword.strip()
    meal_filter_raw = getattr(request, "meal_filter", None)
    meal_filter = meal_filter_raw.strip().title() if isinstance(meal_filter_raw, str) else None
    day_override_raw = getattr(request, "day_override", None)
    if meal_filter and meal_filter not in {"Breakfast", "Lunch", "Dinner"}:
        raise HTTPException(
            status_code=400,
            detail="meal_filter must be one of: Breakfast, Lunch, Dinner",
        )
    try:
        day_override = normalize_day_override(day_override_raw)
    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error)) from error

    applied_day = day_override if day_override else resolve_applied_day(None)
    applied_meal = meal_filter
    apply_day_filter = applied_meal is not None or day_override is not None
    response_applied_day = applied_day if apply_day_filter else None

    origin_resolved: str | None = None
    origin_latitude: float | None = None
    origin_longitude: float | None = None
    if sort_mode == "closest":
        origin_latitude, origin_longitude, origin_resolved = await resolve_origin_coordinates(request)

    try:
        matched_rows = await search_keyword_top_item_per_venue(
            keyword,
            day_of_week=applied_day if apply_day_filter else None,
            meal_filter=applied_meal,
        )
    except RuntimeError as error:
        raise HTTPException(status_code=503, detail=str(error)) from error

    if not matched_rows:
        return {
            "origin_resolved": origin_resolved,
            "keyword": keyword,
            "travel_mode": request.travel_mode,
            "sort_mode": sort_mode,
            "result_mode": result_mode,
            "applied_day": response_applied_day,
            "applied_meal": applied_meal,
            "recommendations": [],
            "per_hall_recommendations": [],
            "message": "No matching protein options found.",
        }

    route_cache: dict[str, dict] = {}
    recommendations = []
    for row in matched_rows:
        venue_id = row["venue_id"]
        if sort_mode == "closest" and venue_id not in route_cache:
            route_cache[venue_id] = await route_distance_to_destination(
                origin_latitude=origin_latitude,
                origin_longitude=origin_longitude,
                destination_latitude=row["venue_lat"],
                destination_longitude=row["venue_lng"],
                travel_mode=request.travel_mode,
            )

        route_result = route_cache.get(venue_id, {})
        recommendations.append(
            {
                "venue_id": venue_id,
                "venue_name": row["venue_name"],
                "venue_category": row["venue_category"],
                "item_name": row["item_name"],
                "protein_grams": row["protein_grams"],
                "calories": row.get("calories"),
                "hours_url": row.get("hours_url"),
                "tags": row["tags"],
                "distance_miles": route_result.get("distance_miles"),
                "duration": route_result.get("duration"),
                "why_selected": (
                    (
                        f"Matched keyword '{keyword}', ranked by closest distance then protein grams."
                        if sort_mode == "closest"
                        else (
                            f"Matched keyword '{keyword}', ranked by highest protein grams."
                            if keyword
                            else "No keyword filter, ranked by highest protein grams."
                        )
                    )
                ),
                "route_error": route_result.get("error"),
            }
        )

    def sort_entries(entries: list[dict]) -> list[dict]:
        if sort_mode == "closest":
            return sorted(
                entries,
                key=lambda entry: (
                    entry["distance_miles"] if entry["distance_miles"] is not None else float("inf"),
                    -entry["protein_grams"],
                ),
            )
        return sorted(
            entries,
            key=lambda entry: (
                -entry["protein_grams"],
                entry["venue_name"],
                entry["item_name"],
            ),
        )

    if result_mode == "global":
        ranked = sort_entries(recommendations)
        if sort_mode == "closest":
            ranked = diversify_closest_global(ranked, request.max_results)
        return {
            "origin_resolved": origin_resolved,
            "keyword": keyword,
            "travel_mode": request.travel_mode,
            "sort_mode": sort_mode,
            "result_mode": result_mode,
            "applied_day": response_applied_day,
            "applied_meal": applied_meal,
            "recommendations": ranked[: request.max_results],
            "per_hall_recommendations": [],
        }

    grouped: dict[str, list[dict]] = {}
    for recommendation in recommendations:
        grouped.setdefault(recommendation["venue_name"], []).append(recommendation)

    per_hall_recommendations = []
    for venue_name, venue_items in grouped.items():
        per_hall_recommendations.append(
            {
                "venue_name": venue_name,
                "items": sort_entries(venue_items)[:per_hall_limit],
            }
        )
    per_hall_recommendations.sort(key=lambda group: group["venue_name"])

    return {
        "origin_resolved": origin_resolved,
        "keyword": keyword,
        "travel_mode": request.travel_mode,
        "sort_mode": sort_mode,
        "result_mode": result_mode,
        "applied_day": response_applied_day,
        "applied_meal": applied_meal,
        "recommendations": [],
        "per_hall_recommendations": per_hall_recommendations,
    }
