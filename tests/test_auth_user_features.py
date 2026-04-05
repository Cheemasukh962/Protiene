import pytest
from fastapi.testclient import TestClient
from starlette import status

import backend.app.main as main_module
from backend.app.main import app


client = TestClient(app)


def test_auth_register_success(monkeypatch: pytest.MonkeyPatch) -> None:
    async def fake_register_user(email: str, password: str) -> dict:
        return {"id": 1, "email": email, "created_at": "2026-04-04T00:00:00+00:00"}

    monkeypatch.setattr(main_module, "register_user", fake_register_user)

    response = client.post(
        "/auth/register",
        json={"email": "student@example.com", "password": "password123"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == 1
    assert data["email"] == "student@example.com"


def test_auth_register_duplicate_email(monkeypatch: pytest.MonkeyPatch) -> None:
    async def fake_register_user(email: str, password: str) -> dict:
        raise ValueError("email is already registered")

    monkeypatch.setattr(main_module, "register_user", fake_register_user)
    response = client.post(
        "/auth/register",
        json={"email": "student@example.com", "password": "password123"},
    )
    assert response.status_code == 400
    assert response.json()["detail"] == "email is already registered"


def test_auth_login_success(monkeypatch: pytest.MonkeyPatch) -> None:
    async def fake_authenticate_user(email: str, password: str) -> dict | None:
        return {"id": 7, "email": email, "is_active": True}

    def fake_create_access_token(user_id: int) -> str:
        return "fake.jwt.token"

    def fake_set_auth_cookie(response: object, token: str) -> None:
        response.set_cookie("dprotein_access_token", token)

    monkeypatch.setattr(main_module, "authenticate_user", fake_authenticate_user)
    monkeypatch.setattr(main_module, "create_access_token", fake_create_access_token)
    monkeypatch.setattr(main_module, "set_auth_cookie", fake_set_auth_cookie)

    response = client.post(
        "/auth/login",
        json={"email": "student@example.com", "password": "password123"},
    )
    assert response.status_code == 200
    assert response.json()["ok"] is True


def test_auth_login_invalid_credentials(monkeypatch: pytest.MonkeyPatch) -> None:
    async def fake_authenticate_user(email: str, password: str) -> dict | None:
        return None

    monkeypatch.setattr(main_module, "authenticate_user", fake_authenticate_user)
    response = client.post(
        "/auth/login",
        json={"email": "student@example.com", "password": "bad"},
    )
    assert response.status_code == 401


def test_auth_login_returns_503_when_jwt_config_missing(monkeypatch: pytest.MonkeyPatch) -> None:
    async def fake_authenticate_user(email: str, password: str) -> dict | None:
        return {"id": 7, "email": email, "is_active": True}

    def fake_create_access_token(user_id: int) -> str:
        raise RuntimeError("JWT_SECRET is required for auth endpoints.")

    monkeypatch.setattr(main_module, "authenticate_user", fake_authenticate_user)
    monkeypatch.setattr(main_module, "create_access_token", fake_create_access_token)

    response = client.post(
        "/auth/login",
        json={"email": "student@example.com", "password": "password123"},
    )
    assert response.status_code == status.HTTP_503_SERVICE_UNAVAILABLE
    assert "JWT_SECRET is required" in response.json()["detail"]


def test_auth_me_success(monkeypatch: pytest.MonkeyPatch) -> None:
    async def fake_resolve_current_user(request: object) -> dict:
        return {"id": 3, "email": "student@example.com", "is_active": True}

    monkeypatch.setattr(main_module, "resolve_current_user", fake_resolve_current_user)
    response = client.get("/auth/me")
    assert response.status_code == 200
    assert response.json()["id"] == 3


def test_auth_me_returns_503_when_jwt_config_missing(monkeypatch: pytest.MonkeyPatch) -> None:
    async def fake_get_current_user_from_request(request: object) -> dict:
        raise RuntimeError("JWT_SECRET is required for auth endpoints.")

    monkeypatch.setattr(main_module, "get_current_user_from_request", fake_get_current_user_from_request)

    response = client.get("/auth/me")
    assert response.status_code == status.HTTP_503_SERVICE_UNAVAILABLE
    assert "JWT_SECRET is required" in response.json()["detail"]


def test_guest_cookie_uses_configured_security_flags(monkeypatch: pytest.MonkeyPatch) -> None:
    async def fake_get_or_create_guest_profile(guest_id_raw: str | None) -> str:
        return "00000000-0000-0000-0000-000000000123"

    async def fake_list_favorites_for_guest(guest_profile_id: str) -> list[dict]:
        return []

    monkeypatch.setattr(main_module, "get_or_create_guest_profile", fake_get_or_create_guest_profile)
    monkeypatch.setattr(main_module, "list_favorites_for_guest", fake_list_favorites_for_guest)
    monkeypatch.setattr(main_module, "COOKIE_SECURE", True)
    monkeypatch.setattr(main_module, "COOKIE_SAMESITE", "none")

    response = client.get("/api/favorites")
    assert response.status_code == 200
    set_cookie = response.headers.get("set-cookie", "")
    assert "dprotein_guest_id=" in set_cookie
    assert "Secure" in set_cookie
    assert "SameSite=none" in set_cookie


def test_user_favorites_requires_auth() -> None:
    unauthenticated_client = TestClient(app)
    response = unauthenticated_client.get("/api/user/favorites")
    assert response.status_code == 401


def test_user_favorites_flow_with_mocked_user(monkeypatch: pytest.MonkeyPatch) -> None:
    async def fake_resolve_current_user(request: object) -> dict:
        return {"id": 99, "email": "student@example.com", "is_active": True}

    async def fake_star_item_for_user(user_id: int, item_name: str) -> dict:
        return {"id": 11, "item_name": item_name, "created_at": "2026-04-04T00:00:00+00:00"}

    async def fake_list_favorites_for_user(user_id: int) -> list[dict]:
        return [{"id": 11, "item_name": "Chicken Burrito Bowl", "created_at": "2026-04-04T00:00:00+00:00"}]

    async def fake_delete_favorite_for_user(user_id: int, favorite_id: int) -> bool:
        return True

    async def fake_tracker_available_now_for_user(user_id: int) -> dict:
        return {"applied_day": "Monday", "applied_meal": "Lunch", "matches": []}

    async def fake_tracker_schedule_for_user(user_id: int) -> dict:
        return {"schedule": [{"item_name": "Chicken Burrito Bowl", "day_of_week": "Monday", "meal": "Lunch"}]}

    async def fake_tracker_overview_for_user(user_id: int, day_override: str | None = None) -> dict:
        return {
            "applied_day": day_override or "Monday",
            "favorites": [
                {
                    "favorite_id": 11,
                    "item_name": "Chicken Burrito Bowl",
                    "available_today": True,
                    "today_slots": [{"day_of_week": "Monday", "meal": "Lunch", "dining_hall": "segundo"}],
                    "schedule": [{"day_of_week": "Monday", "meal": "Lunch", "dining_hall": "segundo"}],
                }
            ],
        }

    monkeypatch.setattr(main_module, "resolve_current_user", fake_resolve_current_user)
    monkeypatch.setattr(main_module, "star_item_for_user", fake_star_item_for_user)
    monkeypatch.setattr(main_module, "list_favorites_for_user", fake_list_favorites_for_user)
    monkeypatch.setattr(main_module, "delete_favorite_for_user", fake_delete_favorite_for_user)
    monkeypatch.setattr(main_module, "tracker_available_now_for_user", fake_tracker_available_now_for_user)
    monkeypatch.setattr(main_module, "tracker_schedule_for_user", fake_tracker_schedule_for_user)
    monkeypatch.setattr(main_module, "tracker_overview_for_user", fake_tracker_overview_for_user)

    r1 = client.post("/api/user/favorites/star", json={"item_name": "Chicken Burrito Bowl"})
    assert r1.status_code == 200
    assert r1.json()["ok"] is True

    r2 = client.get("/api/user/favorites")
    assert r2.status_code == 200
    assert len(r2.json()["favorites"]) == 1

    r3 = client.delete("/api/user/favorites/11")
    assert r3.status_code == 200
    assert r3.json()["ok"] is True

    r4 = client.get("/api/user/tracker/available-now")
    assert r4.status_code == 200
    assert r4.json()["applied_meal"] == "Lunch"

    r5 = client.get("/api/user/tracker/schedule")
    assert r5.status_code == 200
    assert len(r5.json()["schedule"]) == 1

    r6 = client.get("/api/user/tracker/overview?day_override=Monday")
    assert r6.status_code == 200
    assert r6.json()["applied_day"] == "Monday"
    assert len(r6.json()["favorites"]) == 1


def test_guest_tracker_overview_endpoint(monkeypatch: pytest.MonkeyPatch) -> None:
    async def fake_resolve_guest_profile_id(request: object, response: object) -> str:
        return "00000000-0000-0000-0000-000000000123"

    async def fake_tracker_overview_for_guest(
        guest_profile_id: str,
        day_override: str | None = None,
    ) -> dict:
        return {
            "applied_day": day_override or "Tuesday",
            "favorites": [
                {
                    "favorite_id": 1,
                    "item_name": "Lemon Garlic Fried Chicken",
                    "available_today": False,
                    "today_slots": [],
                    "schedule": [{"day_of_week": "Thursday", "meal": "Dinner", "dining_hall": "cuarto"}],
                }
            ],
        }

    monkeypatch.setattr(main_module, "resolve_guest_profile_id", fake_resolve_guest_profile_id)
    monkeypatch.setattr(main_module, "tracker_overview_for_guest", fake_tracker_overview_for_guest)

    response = client.get("/api/tracker/overview?day_override=Tuesday")
    assert response.status_code == 200
    data = response.json()
    assert data["applied_day"] == "Tuesday"
    assert len(data["favorites"]) == 1
