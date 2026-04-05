import pytest
from fastapi.testclient import TestClient

import backend.app.services.recommendations as recommendations_module
from backend.app.main import app


client = TestClient(app)


def test_recommendations_distance_first_then_protein(monkeypatch: pytest.MonkeyPatch) -> None:
    async def fake_search_keyword_top_item_per_venue(
        keyword: str,
        day_of_week: str | None = None,
        meal_filter: str | None = None,
    ) -> list[dict]:
        return [
            {
                "venue_id": 1,
                "venue_name": "Memorial Union Food Court",
                "venue_category": "Food Court",
                "venue_lat": 38.54266,
                "venue_lng": -121.74857,
                "item_name": "Turkey Sandwich",
                "protein_grams": 22,
                "hours_url": "https://example.com/mu",
                "tags": ["sandwich", "turkey"],
            },
            {
                "venue_id": 2,
                "venue_name": "Silo Market",
                "venue_category": "Market",
                "venue_lat": 38.53840,
                "venue_lng": -121.75273,
                "item_name": "Peet's Protein Smoothie",
                "protein_grams": 16,
                "hours_url": "https://example.com/silo",
                "tags": ["smoothie", "protein"],
            },
        ]

    async def fake_route_distance_to_destination(
        origin_latitude: float,
        origin_longitude: float,
        destination_latitude: float,
        destination_longitude: float,
        travel_mode: str = "walking",
    ) -> dict:
        if destination_latitude == 38.53840:
            return {"distance_miles": 0.6, "duration": "540s"}
        return {"distance_miles": 1.2, "duration": "920s"}

    monkeypatch.setattr(
        recommendations_module,
        "search_keyword_top_item_per_venue",
        fake_search_keyword_top_item_per_venue,
    )
    monkeypatch.setattr(
        recommendations_module,
        "route_distance_to_destination",
        fake_route_distance_to_destination,
    )

    response = client.post(
        "/api/recommendations",
        json={
            "origin_mode": "current",
            "origin_latitude": 38.5400,
            "origin_longitude": -121.7500,
            "keyword": "smoothie",
            "travel_mode": "walking",
            "max_results": 5,
            "sort_mode": "closest",
        },
    )

    assert response.status_code == 200
    data = response.json()
    assert len(data["recommendations"]) == 2
    assert data["recommendations"][0]["venue_name"] == "Silo Market"
    assert data["recommendations"][0]["distance_miles"] == pytest.approx(0.6, abs=1e-9)


def test_recommendations_typed_origin_success(monkeypatch: pytest.MonkeyPatch) -> None:
    async def fake_geocode_address(address: str) -> dict:
        return {
            "formatted_address": "Shields Library, Davis, CA",
            "latitude": 38.539,
            "longitude": -121.750,
        }

    async def fake_search_keyword_top_item_per_venue(
        keyword: str,
        day_of_week: str | None = None,
        meal_filter: str | None = None,
    ) -> list[dict]:
        return [
            {
                "venue_id": 2,
                "venue_name": "Silo Market",
                "venue_category": "Market",
                "venue_lat": 38.53840,
                "venue_lng": -121.75273,
                "item_name": "Peet's Protein Smoothie",
                "protein_grams": 16,
                "hours_url": "https://example.com/silo",
                "tags": ["smoothie", "protein"],
            }
        ]

    async def fake_route_distance_to_destination(
        origin_latitude: float,
        origin_longitude: float,
        destination_latitude: float,
        destination_longitude: float,
        travel_mode: str = "walking",
    ) -> dict:
        return {"distance_miles": 0.8, "duration": "600s"}

    monkeypatch.setattr(recommendations_module, "geocode_address", fake_geocode_address)
    monkeypatch.setattr(
        recommendations_module,
        "search_keyword_top_item_per_venue",
        fake_search_keyword_top_item_per_venue,
    )
    monkeypatch.setattr(
        recommendations_module,
        "route_distance_to_destination",
        fake_route_distance_to_destination,
    )

    response = client.post(
        "/api/recommendations",
        json={
            "origin_mode": "typed",
            "origin_text": "Shields Library",
            "keyword": "smoothie",
            "travel_mode": "walking",
            "max_results": 3,
            "sort_mode": "closest",
        },
    )

    assert response.status_code == 200
    data = response.json()
    assert data["origin_resolved"] == "Shields Library, Davis, CA"
    assert data["recommendations"][0]["item_name"] == "Peet's Protein Smoothie"


def test_recommendations_no_matches_returns_empty(monkeypatch: pytest.MonkeyPatch) -> None:
    async def fake_search_keyword_top_item_per_venue(
        keyword: str,
        day_of_week: str | None = None,
        meal_filter: str | None = None,
    ) -> list[dict]:
        return []

    monkeypatch.setattr(
        recommendations_module,
        "search_keyword_top_item_per_venue",
        fake_search_keyword_top_item_per_venue,
    )

    response = client.post(
        "/api/recommendations",
        json={
            "origin_mode": "current",
            "origin_latitude": 38.5400,
            "origin_longitude": -121.7500,
            "keyword": "unmatched_keyword",
            "travel_mode": "walking",
            "max_results": 5,
            "sort_mode": "closest",
        },
    )

    assert response.status_code == 200
    data = response.json()
    assert data["recommendations"] == []
    assert "No matching protein options found" in data["message"]


def test_recommendations_invalid_origin_mode(monkeypatch: pytest.MonkeyPatch) -> None:
    response = client.post(
        "/api/recommendations",
        json={
            "origin_mode": "invalid_mode",
            "keyword": "smoothie",
            "travel_mode": "walking",
            "max_results": 5,
            "sort_mode": "closest",
        },
    )

    assert response.status_code == 400
    assert response.json()["detail"] == "origin_mode must be 'current' or 'typed'"


def test_recommendations_default_protein_mode_without_origin(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    async def fake_search_keyword_top_item_per_venue(
        keyword: str,
        day_of_week: str | None = None,
        meal_filter: str | None = None,
    ) -> list[dict]:
        return [
            {
                "venue_id": "segundo",
                "venue_name": "Segundo Dining Commons",
                "venue_category": "Dining Hall",
                "venue_lat": 38.54161,
                "venue_lng": -121.75774,
                "item_name": "Item A",
                "protein_grams": 20,
                "hours_url": "https://example.com/segundo",
                "tags": [],
            },
            {
                "venue_id": "tercero",
                "venue_name": "Tercero Dining Commons",
                "venue_category": "Dining Hall",
                "venue_lat": 38.54453,
                "venue_lng": -121.74989,
                "item_name": "Item B",
                "protein_grams": 40,
                "hours_url": "https://example.com/tercero",
                "tags": [],
            },
        ]

    async def fake_route_distance_to_destination(
        origin_latitude: float,
        origin_longitude: float,
        destination_latitude: float,
        destination_longitude: float,
        travel_mode: str = "walking",
    ) -> dict:
        raise AssertionError("Distance API should not be called in protein mode")

    monkeypatch.setattr(
        recommendations_module,
        "search_keyword_top_item_per_venue",
        fake_search_keyword_top_item_per_venue,
    )
    monkeypatch.setattr(
        recommendations_module,
        "route_distance_to_destination",
        fake_route_distance_to_destination,
    )

    response = client.post(
        "/api/recommendations",
        json={
            "keyword": "",
            "max_results": 5,
        },
    )

    assert response.status_code == 200
    data = response.json()
    assert data["sort_mode"] == "protein"
    assert data["recommendations"][0]["item_name"] == "Item B"
    assert data["recommendations"][1]["item_name"] == "Item A"


def test_recommendations_closest_global_diversifies_halls(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    async def fake_search_keyword_top_item_per_venue(
        keyword: str,
        day_of_week: str | None = None,
        meal_filter: str | None = None,
    ) -> list[dict]:
        return [
            {
                "venue_id": "tercero",
                "venue_name": "Tercero Dining Commons",
                "venue_category": "Dining Hall",
                "venue_lat": 38.54453,
                "venue_lng": -121.74989,
                "item_name": "T Item 1",
                "protein_grams": 30,
                "calories": 400,
                "hours_url": "https://example.com/tercero",
                "tags": [],
            },
            {
                "venue_id": "tercero",
                "venue_name": "Tercero Dining Commons",
                "venue_category": "Dining Hall",
                "venue_lat": 38.54453,
                "venue_lng": -121.74989,
                "item_name": "T Item 2",
                "protein_grams": 20,
                "calories": 300,
                "hours_url": "https://example.com/tercero",
                "tags": [],
            },
            {
                "venue_id": "segundo",
                "venue_name": "Segundo Dining Commons",
                "venue_category": "Dining Hall",
                "venue_lat": 38.54161,
                "venue_lng": -121.75774,
                "item_name": "S Item 1",
                "protein_grams": 25,
                "calories": 350,
                "hours_url": "https://example.com/segundo",
                "tags": [],
            },
        ]

    async def fake_route_distance_to_destination(
        origin_latitude: float,
        origin_longitude: float,
        destination_latitude: float,
        destination_longitude: float,
        travel_mode: str = "walking",
    ) -> dict:
        if destination_latitude == 38.54453:
            return {"distance_miles": 0.4, "duration": "500s"}
        return {"distance_miles": 0.7, "duration": "900s"}

    monkeypatch.setattr(
        recommendations_module,
        "search_keyword_top_item_per_venue",
        fake_search_keyword_top_item_per_venue,
    )
    monkeypatch.setattr(
        recommendations_module,
        "route_distance_to_destination",
        fake_route_distance_to_destination,
    )

    response = client.post(
        "/api/recommendations",
        json={
            "origin_mode": "current",
            "origin_latitude": 38.5400,
            "origin_longitude": -121.7500,
            "keyword": "chicken",
            "travel_mode": "walking",
            "max_results": 3,
            "sort_mode": "closest",
            "result_mode": "global",
        },
    )

    assert response.status_code == 200
    data = response.json()
    venues = [entry["venue_name"] for entry in data["recommendations"]]
    assert venues[0] == "Tercero Dining Commons"
    assert venues[1] == "Segundo Dining Commons"


def test_recommendations_with_meal_filter_applies_day_and_meal(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    captured_day: str | None = None
    captured_meal: str | None = None

    async def fake_search_keyword_top_item_per_venue(
        keyword: str,
        day_of_week: str | None = None,
        meal_filter: str | None = None,
    ) -> list[dict]:
        nonlocal captured_day, captured_meal
        captured_day = day_of_week
        captured_meal = meal_filter
        return [
            {
                "venue_id": "segundo",
                "venue_name": "Segundo Dining Commons",
                "venue_category": "Dining Hall",
                "venue_lat": 38.54161,
                "venue_lng": -121.75774,
                "item_name": "Chicken Bowl",
                "protein_grams": 33,
                "calories": 420,
                "hours_url": "https://housing.ucdavis.edu/dining/dining-commons/segundo/",
                "tags": [],
            }
        ]

    monkeypatch.setattr(
        recommendations_module,
        "search_keyword_top_item_per_venue",
        fake_search_keyword_top_item_per_venue,
    )

    response = client.post(
        "/api/recommendations",
        json={
            "keyword": "chicken",
            "meal_filter": "Lunch",
            "day_override": "Monday",
            "max_results": 5,
        },
    )

    assert response.status_code == 200
    data = response.json()
    assert captured_day == "Monday"
    assert captured_meal == "Lunch"
    assert data["applied_day"] == "Monday"
    assert data["applied_meal"] == "Lunch"
    assert data["recommendations"][0]["hours_url"].startswith("https://")


def test_recommendations_rejects_invalid_day_override() -> None:
    response = client.post(
        "/api/recommendations",
        json={
            "keyword": "chicken",
            "meal_filter": "Lunch",
            "day_override": "Funday",
            "max_results": 5,
        },
    )

    assert response.status_code == 400
    assert "day_override must be one of" in response.json()["detail"]
