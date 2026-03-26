import pytest
from fastapi.testclient import TestClient

import backend.app.main as main_module
from backend.app.main import app


client = TestClient(app)


def test_user_testing_current_mode_uses_passed_coordinates(monkeypatch: pytest.MonkeyPatch) -> None:
    async def fake_route_distance_to_destination(
        origin_latitude: float,
        origin_longitude: float,
        destination_latitude: float,
        destination_longitude: float,
    ) -> dict:
        return {"distance_miles": 2.7, "duration": "640s"}

    monkeypatch.setattr(main_module, "route_distance_to_destination", fake_route_distance_to_destination)

    response = client.post(
        "/api/user-testing",
        json={
            "origin_mode": "current",
            "origin_latitude": 38.55,
            "origin_longitude": -121.75,
            "food_query": "protein bowl",
        },
    )

    assert response.status_code == 200
    data = response.json()
    assert data["origin_mode"] == "current"
    assert data["food_query"] == "protein bowl"
    assert data["route_preview_to_silo_miles"] == pytest.approx(2.7, abs=1e-9)


def test_user_testing_typed_mode_geocodes_address(monkeypatch: pytest.MonkeyPatch) -> None:
    async def fake_geocode_address(address: str) -> dict:
        return {
            "formatted_address": "Shields Library, Davis, CA",
            "latitude": 38.539,
            "longitude": -121.75,
        }

    async def fake_route_distance_to_destination(
        origin_latitude: float,
        origin_longitude: float,
        destination_latitude: float,
        destination_longitude: float,
    ) -> dict:
        return {"distance_miles": 1.9, "duration": "510s"}

    monkeypatch.setattr(main_module, "geocode_address", fake_geocode_address)
    monkeypatch.setattr(main_module, "route_distance_to_destination", fake_route_distance_to_destination)

    response = client.post(
        "/api/user-testing",
        json={
            "origin_mode": "typed",
            "origin_text": "Shields Library",
            "food_query": "chicken",
        },
    )

    assert response.status_code == 200
    data = response.json()
    assert data["origin_mode"] == "typed"
    assert data["origin_label"] == "Shields Library, Davis, CA"
    assert data["route_preview_to_silo_miles"] == pytest.approx(1.9, abs=1e-9)
