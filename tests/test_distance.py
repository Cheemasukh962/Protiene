import pytest
from fastapi.testclient import TestClient

import backend.app.main as main_module
from backend.app.main import app


client = TestClient(app)


def test_distance_endpoint_returns_numeric_miles(monkeypatch: pytest.MonkeyPatch) -> None:
    async def fake_geocode_address(address: str) -> dict:
        return {
            "formatted_address": "Silo Market, Davis, CA",
            "latitude": 38.5384,
            "longitude": -121.7527,
        }

    async def fake_route_distance_to_destination(
        origin_latitude: float,
        origin_longitude: float,
        destination_latitude: float,
        destination_longitude: float,
        travel_mode: str = "driving",
    ) -> dict:
        return {"travel_mode": "DRIVE", "distance_miles": 2.7, "duration": "640s"}

    monkeypatch.setattr(main_module, "geocode_address", fake_geocode_address)
    monkeypatch.setattr(main_module, "route_distance_to_destination", fake_route_distance_to_destination)

    response = client.post(
        "/api/distance",
        json={
            "origin_mode": "current",
            "origin_latitude": 38.55,
            "origin_longitude": -121.75,
            "destination_text": "Silo Market Davis",
            "travel_mode": "driving",
        },
    )

    assert response.status_code == 200
    data = response.json()
    assert isinstance(data["distance_miles"], float)
    assert data["travel_mode"] == "DRIVE"
    assert data["distance_miles"] == pytest.approx(2.7, abs=1e-9)
    assert data["destination_resolved"] == "Silo Market, Davis, CA"


def test_distance_endpoint_returns_400_when_destination_not_found(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    async def fake_geocode_address(address: str) -> dict:
        return {"error": "No matching address found"}

    monkeypatch.setattr(main_module, "geocode_address", fake_geocode_address)

    response = client.post(
        "/api/distance",
        json={
            "origin_mode": "current",
            "origin_latitude": 38.55,
            "origin_longitude": -121.75,
            "destination_text": "unknown place",
            "travel_mode": "driving",
        },
    )

    assert response.status_code == 400
    assert response.json()["detail"] == "No matching address found"


def test_distance_endpoint_allows_typed_origin(monkeypatch: pytest.MonkeyPatch) -> None:
    async def fake_geocode_address(address: str) -> dict:
        if "Shields" in address:
            return {
                "formatted_address": "Shields Library, Davis, CA",
                "latitude": 38.539,
                "longitude": -121.750,
            }
        return {
            "formatted_address": "Silo Market, Davis, CA",
            "latitude": 38.5384,
            "longitude": -121.7527,
        }

    async def fake_route_distance_to_destination(
        origin_latitude: float,
        origin_longitude: float,
        destination_latitude: float,
        destination_longitude: float,
        travel_mode: str = "driving",
    ) -> dict:
        return {"travel_mode": "WALK", "distance_miles": 1.2, "duration": "360s"}

    monkeypatch.setattr(main_module, "geocode_address", fake_geocode_address)
    monkeypatch.setattr(main_module, "route_distance_to_destination", fake_route_distance_to_destination)

    response = client.post(
        "/api/distance",
        json={
            "origin_mode": "typed",
            "origin_text": "Shields Library",
            "destination_text": "Silo Market",
            "travel_mode": "walking",
        },
    )

    assert response.status_code == 200
    data = response.json()
    assert data["origin_mode"] == "typed"
    assert data["origin_resolved"] == "Shields Library, Davis, CA"
    assert data["travel_mode"] == "WALK"
    assert data["distance_miles"] == pytest.approx(1.2, abs=1e-9)
