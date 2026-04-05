from datetime import datetime
from typing import Any

from backend.app.services.auth import ensure_auth_tables
from backend.app.services.day_filters import resolve_applied_day
from backend.app.services.postgres_db import _ensure_pool


CREATE_USER_FAVORITES_SQL = """
CREATE TABLE IF NOT EXISTS user_favorite_items (
    id BIGSERIAL PRIMARY KEY,
    user_id BIGINT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    item_name_normalized TEXT NOT NULL,
    item_name_original TEXT NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE (user_id, item_name_normalized)
);

CREATE INDEX IF NOT EXISTS idx_user_favorite_items_user_id
    ON user_favorite_items(user_id);
"""


def normalize_item_name(item_name: str) -> str:
    return " ".join(item_name.strip().lower().split())


def infer_current_day_and_meal() -> tuple[str, str | None]:
    now_local = datetime.now()
    day_name = now_local.strftime("%A")
    minutes = now_local.hour * 60 + now_local.minute

    if 6 * 60 <= minutes <= 10 * 60 + 59:
        return day_name, "Breakfast"
    if 11 * 60 <= minutes <= 16 * 60 + 59:
        return day_name, "Lunch"
    if 17 * 60 <= minutes <= 21 * 60 + 59:
        return day_name, "Dinner"
    return day_name, None


async def ensure_user_favorites_tables() -> None:
    await ensure_auth_tables()
    pool = await _ensure_pool()
    async with pool.acquire() as connection:
        await connection.execute(CREATE_USER_FAVORITES_SQL)


async def star_item_for_user(user_id: int, item_name: str) -> dict:
    await ensure_user_favorites_tables()
    normalized = normalize_item_name(item_name)
    if not normalized:
        raise ValueError("item_name is required")

    pool = await _ensure_pool()
    async with pool.acquire() as connection:
        row = await connection.fetchrow(
            """
            INSERT INTO user_favorite_items(user_id, item_name_normalized, item_name_original)
            VALUES($1, $2, $3)
            ON CONFLICT (user_id, item_name_normalized)
            DO UPDATE SET item_name_original = EXCLUDED.item_name_original
            RETURNING id, item_name_original, created_at
            """,
            user_id,
            normalized,
            item_name.strip(),
        )

    return {
        "id": row["id"],
        "item_name": row["item_name_original"],
        "created_at": row["created_at"].isoformat(),
    }


async def list_favorites_for_user(user_id: int) -> list[dict]:
    await ensure_user_favorites_tables()
    pool = await _ensure_pool()
    async with pool.acquire() as connection:
        rows = await connection.fetch(
            """
            SELECT id, item_name_original, created_at
            FROM user_favorite_items
            WHERE user_id = $1
            ORDER BY created_at DESC
            """,
            user_id,
        )
    return [
        {
            "id": row["id"],
            "item_name": row["item_name_original"],
            "created_at": row["created_at"].isoformat(),
        }
        for row in rows
    ]


async def delete_favorite_for_user(user_id: int, favorite_id: int) -> bool:
    await ensure_user_favorites_tables()
    pool = await _ensure_pool()
    async with pool.acquire() as connection:
        result = await connection.execute(
            """
            DELETE FROM user_favorite_items
            WHERE id = $1 AND user_id = $2
            """,
            favorite_id,
            user_id,
        )
    return result.endswith("1")


async def tracker_available_now_for_user(user_id: int) -> dict[str, Any]:
    await ensure_user_favorites_tables()
    day_name, meal_name = infer_current_day_and_meal()
    if meal_name is None:
        return {"applied_day": day_name, "applied_meal": None, "matches": []}

    pool = await _ensure_pool()
    async with pool.acquire() as connection:
        rows = await connection.fetch(
            """
            SELECT
                td.dining_hall,
                td.item_name,
                MAX(td.protein_g) AS protein_g,
                MAX(td.calories) AS calories,
                td.day_of_week,
                td.meal
            FROM public."TestData" td
            JOIN user_favorite_items ufi
              ON ufi.user_id = $1
             AND ufi.item_name_normalized = LOWER(TRIM(td.item_name))
            WHERE td.day_of_week = $2
              AND td.meal = $3
              AND td.protein_g IS NOT NULL
            GROUP BY td.dining_hall, td.item_name, td.day_of_week, td.meal
            ORDER BY td.dining_hall ASC, MAX(td.protein_g) DESC
            """,
            user_id,
            day_name,
            meal_name,
        )

    matches = []
    for row in rows:
        matches.append(
            {
                "dining_hall": row["dining_hall"],
                "item_name": row["item_name"],
                "protein_grams": float(row["protein_g"]),
                "calories": float(row["calories"]) if row["calories"] is not None else None,
                "day_of_week": row["day_of_week"],
                "meal": row["meal"],
            }
        )

    return {"applied_day": day_name, "applied_meal": meal_name, "matches": matches}


async def tracker_schedule_for_user(user_id: int) -> dict[str, Any]:
    await ensure_user_favorites_tables()
    pool = await _ensure_pool()
    async with pool.acquire() as connection:
        rows = await connection.fetch(
            """
            SELECT
                td.item_name,
                td.dining_hall,
                td.day_of_week,
                td.meal,
                MAX(td.protein_g) AS protein_g,
                MAX(td.calories) AS calories
            FROM public."TestData" td
            JOIN user_favorite_items ufi
              ON ufi.user_id = $1
             AND ufi.item_name_normalized = LOWER(TRIM(td.item_name))
            WHERE td.protein_g IS NOT NULL
            GROUP BY td.item_name, td.dining_hall, td.day_of_week, td.meal
            ORDER BY td.item_name, td.day_of_week, td.meal, td.dining_hall
            """,
            user_id,
        )

    schedule = []
    for row in rows:
        schedule.append(
            {
                "item_name": row["item_name"],
                "dining_hall": row["dining_hall"],
                "day_of_week": row["day_of_week"],
                "meal": row["meal"],
                "protein_grams": float(row["protein_g"]),
                "calories": float(row["calories"]) if row["calories"] is not None else None,
            }
        )
    return {"schedule": schedule}


async def tracker_overview_for_user(
    user_id: int,
    day_override: str | None = None,
) -> dict[str, Any]:
    await ensure_user_favorites_tables()
    applied_day = resolve_applied_day(day_override)

    pool = await _ensure_pool()
    async with pool.acquire() as connection:
        favorites_rows = await connection.fetch(
            """
            SELECT id, item_name_original, created_at
            FROM user_favorite_items
            WHERE user_id = $1
            ORDER BY created_at DESC
            """,
            user_id,
        )
        schedule_rows = await connection.fetch(
            """
            SELECT
                ufi.id AS favorite_id,
                td.item_name AS item_name,
                td.dining_hall,
                td.day_of_week,
                td.meal,
                MAX(td.protein_g) AS protein_g,
                MAX(td.calories) AS calories
            FROM user_favorite_items ufi
            JOIN public."TestData" td
              ON ufi.item_name_normalized = LOWER(TRIM(td.item_name))
            WHERE ufi.user_id = $1
              AND td.protein_g IS NOT NULL
            GROUP BY ufi.id, td.item_name, td.dining_hall, td.day_of_week, td.meal
            ORDER BY
              ufi.id,
              CASE td.day_of_week
                WHEN 'Monday' THEN 1
                WHEN 'Tuesday' THEN 2
                WHEN 'Wednesday' THEN 3
                WHEN 'Thursday' THEN 4
                WHEN 'Friday' THEN 5
                WHEN 'Saturday' THEN 6
                WHEN 'Sunday' THEN 7
                ELSE 99
              END,
              CASE td.meal
                WHEN 'Breakfast' THEN 1
                WHEN 'Lunch' THEN 2
                WHEN 'Dinner' THEN 3
                ELSE 99
              END,
              td.dining_hall ASC
            """,
            user_id,
        )

    favorites_map: dict[int, dict[str, Any]] = {}
    ordered_favorites: list[dict[str, Any]] = []

    for row in favorites_rows:
        favorite = {
            "favorite_id": row["id"],
            "item_name": row["item_name_original"],
            "available_today": False,
            "today_slots": [],
            "schedule": [],
        }
        favorites_map[row["id"]] = favorite
        ordered_favorites.append(favorite)

    for row in schedule_rows:
        favorite = favorites_map.get(row["favorite_id"])
        if favorite is None:
            continue

        slot = {
            "item_name": row["item_name"],
            "dining_hall": row["dining_hall"],
            "day_of_week": row["day_of_week"],
            "meal": row["meal"],
            "protein_grams": float(row["protein_g"]),
            "calories": float(row["calories"]) if row["calories"] is not None else None,
        }
        favorite["schedule"].append(slot)

        if row["day_of_week"] == applied_day:
            favorite["today_slots"].append(slot)
            favorite["available_today"] = True

    return {"applied_day": applied_day, "favorites": ordered_favorites}
