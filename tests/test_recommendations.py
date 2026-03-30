import pytest
from fastapi.testclient import TestClient

import backend.app.services.recommendations as recommendations_module
from backend.app.main import app


client = TestClient(app)


def test_recommendations_distance_first_then_protein(monkeypatch: pytest.MonkeyPatch) -> None:
    async def fake_search_keyword_top_item_per_venue(keyword: str) -> list[dict]:
        return [
            {
                "venue_id": 1,
                "venue_name": "Memorial Union Food Court",
                "venue_category": "Food Court",
                "venue_lat": 38.54266,
                "venue_lng": -121.74857,
                "item_name": "Turkey Sandwich",
                "protein_grams": 22,
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

    async def fake_search_keyword_top_item_per_venue(keyword: str) -> list[dict]:
        return [
            {
                "venue_id": 2,
                "venue_name": "Silo Market",
                "venue_category": "Market",
                "venue_lat": 38.53840,
                "venue_lng": -121.75273,
                "item_name": "Peet's Protein Smoothie",
                "protein_grams": 16,
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
        },
    )

    assert response.status_code == 200
    data = response.json()
    assert data["origin_resolved"] == "Shields Library, Davis, CA"
    assert data["recommendations"][0]["item_name"] == "Peet's Protein Smoothie"


def test_recommendations_no_matches_returns_empty(monkeypatch: pytest.MonkeyPatch) -> None:
    async def fake_search_keyword_top_item_per_venue(keyword: str) -> list[dict]:
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
        },
    )

    assert response.status_code == 400
    assert response.json()["detail"] == "origin_mode must be 'current' or 'typed'"
