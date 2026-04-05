from datetime import datetime
from typing import Any
from uuid import UUID
from uuid import uuid4

from backend.app.services.day_filters import resolve_applied_day
from backend.app.services.postgres_db import _ensure_pool


CREATE_FAVORITES_SQL = """
CREATE TABLE IF NOT EXISTS guest_profiles (
    id UUID PRIMARY KEY,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    last_seen_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS favorite_items (
    id BIGSERIAL PRIMARY KEY,
    guest_profile_id UUID NOT NULL REFERENCES guest_profiles(id) ON DELETE CASCADE,
    item_name_normalized TEXT NOT NULL,
    item_name_original TEXT NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE (guest_profile_id, item_name_normalized)
);

CREATE INDEX IF NOT EXISTS idx_favorite_items_guest_profile_id
    ON favorite_items(guest_profile_id);
"""


def normalize_item_name(item_name: str) -> str:
    return " ".join(item_name.strip().lower().split())


def infer_current_day_and_meal() -> tuple[str, str | None]:
    # Use host local time for meal/day inference to avoid hard dependency on tzdata.
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


async def ensure_favorites_tables() -> None:
    pool = await _ensure_pool()
    async with pool.acquire() as connection:
        await connection.execute(CREATE_FAVORITES_SQL)


async def get_or_create_guest_profile(guest_id_raw: str | None) -> str:
    await ensure_favorites_tables()
    pool = await _ensure_pool()

    candidate_id: str | None = None
    if guest_id_raw:
        try:
            candidate_id = str(UUID(guest_id_raw))
        except ValueError:
            candidate_id = None

    async with pool.acquire() as connection:
        if candidate_id:
            existing = await connection.fetchval(
                "SELECT id::text FROM guest_profiles WHERE id = $1::uuid",
                candidate_id,
            )
            if existing:
                await connection.execute(
                    "UPDATE guest_profiles SET last_seen_at = NOW() WHERE id = $1::uuid",
                    candidate_id,
                )
                return candidate_id

        new_id = str(uuid4())
        await connection.execute(
            "INSERT INTO guest_profiles(id) VALUES($1::uuid)",
            new_id,
        )
        return new_id


async def star_item_for_guest(guest_profile_id: str, item_name: str) -> dict:
    normalized = normalize_item_name(item_name)
    if not normalized:
        raise ValueError("item_name is required")

    pool = await _ensure_pool()
    async with pool.acquire() as connection:
        row = await connection.fetchrow(
            """
            INSERT INTO favorite_items(guest_profile_id, item_name_normalized, item_name_original)
            VALUES($1::uuid, $2, $3)
            ON CONFLICT (guest_profile_id, item_name_normalized)
            DO UPDATE SET item_name_original = EXCLUDED.item_name_original
            RETURNING id, item_name_original, created_at
            """,
            guest_profile_id,
            normalized,
            item_name.strip(),
        )

    return {
        "id": row["id"],
        "item_name": row["item_name_original"],
        "created_at": row["created_at"].isoformat(),
    }


async def list_favorites_for_guest(guest_profile_id: str) -> list[dict]:
    pool = await _ensure_pool()
    async with pool.acquire() as connection:
        rows = await connection.fetch(
            """
            SELECT id, item_name_original, created_at
            FROM favorite_items
            WHERE guest_profile_id = $1::uuid
            ORDER BY created_at DESC
            """,
            guest_profile_id,
        )
    return [
        {
            "id": row["id"],
            "item_name": row["item_name_original"],
            "created_at": row["created_at"].isoformat(),
        }
        for row in rows
    ]


async def delete_favorite_for_guest(guest_profile_id: str, favorite_id: int) -> bool:
    pool = await _ensure_pool()
    async with pool.acquire() as connection:
        result = await connection.execute(
            """
            DELETE FROM favorite_items
            WHERE id = $1 AND guest_profile_id = $2::uuid
            """,
            favorite_id,
            guest_profile_id,
        )
    return result.endswith("1")


async def tracker_available_now_for_guest(guest_profile_id: str) -> dict[str, Any]:
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
            JOIN favorite_items fi
              ON fi.guest_profile_id = $1::uuid
             AND fi.item_name_normalized = LOWER(TRIM(td.item_name))
            WHERE td.day_of_week = $2
              AND td.meal = $3
              AND td.protein_g IS NOT NULL
            GROUP BY td.dining_hall, td.item_name, td.day_of_week, td.meal
            ORDER BY td.dining_hall ASC, MAX(td.protein_g) DESC
            """,
            guest_profile_id,
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


async def tracker_schedule_for_guest(guest_profile_id: str) -> dict[str, Any]:
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
            JOIN favorite_items fi
              ON fi.guest_profile_id = $1::uuid
             AND fi.item_name_normalized = LOWER(TRIM(td.item_name))
            WHERE td.protein_g IS NOT NULL
            GROUP BY td.item_name, td.dining_hall, td.day_of_week, td.meal
            ORDER BY td.item_name, td.day_of_week, td.meal, td.dining_hall
            """,
            guest_profile_id,
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


async def tracker_overview_for_guest(
    guest_profile_id: str,
    day_override: str | None = None,
) -> dict[str, Any]:
    await ensure_favorites_tables()
    applied_day = resolve_applied_day(day_override)

    pool = await _ensure_pool()
    async with pool.acquire() as connection:
        favorites_rows = await connection.fetch(
            """
            SELECT id, item_name_original, created_at
            FROM favorite_items
            WHERE guest_profile_id = $1::uuid
            ORDER BY created_at DESC
            """,
            guest_profile_id,
        )
        schedule_rows = await connection.fetch(
            """
            SELECT
                fi.id AS favorite_id,
                td.item_name AS item_name,
                td.dining_hall,
                td.day_of_week,
                td.meal,
                MAX(td.protein_g) AS protein_g,
                MAX(td.calories) AS calories
            FROM favorite_items fi
            JOIN public."TestData" td
              ON fi.item_name_normalized = LOWER(TRIM(td.item_name))
            WHERE fi.guest_profile_id = $1::uuid
              AND td.protein_g IS NOT NULL
            GROUP BY fi.id, td.item_name, td.dining_hall, td.day_of_week, td.meal
            ORDER BY
              fi.id,
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
            guest_profile_id,
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
