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


def test_route_endpoint_returns_miles_and_polyline(monkeypatch: pytest.MonkeyPatch) -> None:
    async def fake_geocode_address(address: str) -> dict:
        return {
            "formatted_address": "Memorial Union, Davis, CA",
            "latitude": 38.54266,
            "longitude": -121.74857,
        }

    async def fake_route_distance_to_destination(
        origin_latitude: float,
        origin_longitude: float,
        destination_latitude: float,
        destination_longitude: float,
        travel_mode: str = "driving",
    ) -> dict:
        return {
            "travel_mode": "WALK",
            "distance_miles": 0.62,
            "duration": "780s",
            "encoded_polyline": "abc123",
        }

    monkeypatch.setattr(main_module, "geocode_address", fake_geocode_address)
    monkeypatch.setattr(main_module, "route_distance_to_destination", fake_route_distance_to_destination)

    response = client.post(
        "/api/route",
        json={
            "origin_mode": "current",
            "origin_latitude": 38.54,
            "origin_longitude": -121.75,
            "destination_text": "Memorial Union, Davis CA",
            "travel_mode": "walking",
        },
    )

    assert response.status_code == 200
    data = response.json()
    assert isinstance(data["distance_miles"], float)
    assert data["distance_miles"] == pytest.approx(0.62, abs=1e-9)
    assert isinstance(data["encoded_polyline"], str)
    assert len(data["encoded_polyline"]) > 0


def test_route_endpoint_typed_origin_geocodes_both_locations(monkeypatch: pytest.MonkeyPatch) -> None:
    seen_queries: list[str] = []

    async def fake_geocode_address(address: str) -> dict:
        seen_queries.append(address)
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
        return {
            "travel_mode": "DRIVE",
            "distance_miles": 1.0,
            "duration": "320s",
            "encoded_polyline": "xyz987",
        }

    monkeypatch.setattr(main_module, "geocode_address", fake_geocode_address)
    monkeypatch.setattr(main_module, "route_distance_to_destination", fake_route_distance_to_destination)

    response = client.post(
        "/api/route",
        json={
            "origin_mode": "typed",
            "origin_text": "Shields Library",
            "destination_text": "Silo Market",
            "travel_mode": "driving",
        },
    )

    assert response.status_code == 200
    assert seen_queries == ["Shields Library", "Silo Market"]


def test_route_endpoint_invalid_destination_returns_400(monkeypatch: pytest.MonkeyPatch) -> None:
    async def fake_geocode_address(address: str) -> dict:
        return {"error": "No matching address found"}

    monkeypatch.setattr(main_module, "geocode_address", fake_geocode_address)

    response = client.post(
        "/api/route",
        json={
            "origin_mode": "current",
            "origin_latitude": 38.54,
            "origin_longitude": -121.75,
            "destination_text": "unknown place",
            "travel_mode": "walking",
        },
    )

    assert response.status_code == 400
    assert response.json()["detail"] == "No matching address found"


def test_route_endpoint_passes_travel_mode(monkeypatch: pytest.MonkeyPatch) -> None:
    captured_mode = {"value": ""}

    async def fake_geocode_address(address: str) -> dict:
        return {
            "formatted_address": "Memorial Union, Davis, CA",
            "latitude": 38.54266,
            "longitude": -121.74857,
        }

    async def fake_route_distance_to_destination(
        origin_latitude: float,
        origin_longitude: float,
        destination_latitude: float,
        destination_longitude: float,
        travel_mode: str = "driving",
    ) -> dict:
        captured_mode["value"] = travel_mode
        return {
            "travel_mode": "WALK",
            "distance_miles": 0.8,
            "duration": "900s",
            "encoded_polyline": "poly123",
        }

    monkeypatch.setattr(main_module, "geocode_address", fake_geocode_address)
    monkeypatch.setattr(main_module, "route_distance_to_destination", fake_route_distance_to_destination)

    response = client.post(
        "/api/route",
        json={
            "origin_mode": "current",
            "origin_latitude": 38.54,
            "origin_longitude": -121.75,
            "destination_text": "Memorial Union",
            "travel_mode": "walking",
        },
    )

    assert response.status_code == 200
    assert captured_mode["value"] == "walking"
    assert response.json()["travel_mode"] == "WALK"
