import pytest
from fastapi.testclient import TestClient

from backend.app.main import app, calculate_distance_miles


client = TestClient(app)


def test_same_coordinates_return_zero_distance() -> None:
    distance = calculate_distance_miles(38.53830, -121.76168, 38.53830, -121.76168)

    assert distance == pytest.approx(0.0, abs=1e-9)


def test_distance_is_symmetric() -> None:
    forward_distance = calculate_distance_miles(38.53830, -121.76168, 38.54161, -121.75774)
    reverse_distance = calculate_distance_miles(38.54161, -121.75774, 38.53830, -121.76168)

    assert forward_distance == pytest.approx(reverse_distance)


def test_different_coordinates_return_positive_distance() -> None:
    distance = calculate_distance_miles(38.53830, -121.76168, 38.54266, -121.74857)

    assert distance > 0


def test_nearest_campus_location_endpoint_returns_closest_place() -> None:
    response = client.post(
        "/api/campus/nearest",
        json={"latitude": 38.53830, "longitude": -121.76168},
    )

    assert response.status_code == 200
    assert response.json()["name"] == "Silo"
    assert response.json()["distance_miles"] == pytest.approx(0.0, abs=1e-9)
