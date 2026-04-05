from typing import Any

from backend.app.config import POSTGRES_DSN

try:
    import asyncpg
except ImportError:  # pragma: no cover - handled at runtime in environments without asyncpg
    asyncpg = None


_pool: Any = None

HALL_COORDS = {
    "segundo": {
        "venue_name": "Segundo Dining Commons",
        "venue_category": "Dining Hall",
        "venue_lat": 38.54161,
        "venue_lng": -121.75774,
    },
    "tercero": {
        "venue_name": "Tercero Dining Commons",
        "venue_category": "Dining Hall",
        "venue_lat": 38.54453,
        "venue_lng": -121.74989,
    },
    "cuarto": {
        "venue_name": "Cuarto Dining Commons",
        "venue_category": "Dining Hall",
        "venue_lat": 38.53595,
        "venue_lng": -121.76145,
    },
    "latitude": {
        "venue_name": "Latitude Restaurant",
        "venue_category": "Dining Hall",
        "venue_lat": 38.54758,
        "venue_lng": -121.75953,
    },
}

HALL_HOURS_URLS = {
    "segundo": "https://housing.ucdavis.edu/dining/dining-commons/segundo/",
    "tercero": "https://housing.ucdavis.edu/dining/dining-commons/tercero/",
    "cuarto": "https://housing.ucdavis.edu/dining/dining-commons/cuarto/",
    "latitude": "https://housing.ucdavis.edu/dining/dining-commons/latitude/",
}


async def _ensure_pool() -> Any:
    global _pool

    if asyncpg is None:
        raise RuntimeError("asyncpg is not installed. Install dependencies from requirements.txt.")
    if not POSTGRES_DSN:
        raise RuntimeError("POSTGRES_DSN is required to use recommendations.")

    if _pool is None:
        _pool = await asyncpg.create_pool(dsn=POSTGRES_DSN, min_size=1, max_size=5)
    return _pool


async def search_keyword_top_item_per_venue(
    keyword: str,
    day_of_week: str | None = None,
    meal_filter: str | None = None,
) -> list[dict]:
    """
    Query imported dining-hall rows from public."TestData".
    Returns item-level candidates (deduped by hall + item) across all halls.
    """

    keyword_clean = keyword.strip().lower()
    like_pattern = f"%{keyword_clean}%"
    # This SQL is the core data source for recommendations.
    # It dedupes repeated menu rows and keeps strongest nutrition values per hall+item.
    sql = """
    WITH normalized AS (
      SELECT
        LOWER(td.dining_hall) AS hall_key,
        td.item_name,
        MAX(td.protein_g) AS protein_g,
        MAX(td.calories) AS calories,
        MAX(td.source_url) AS source_url
      FROM public."TestData" td
      WHERE td.protein_g IS NOT NULL
        AND LOWER(td.dining_hall) = ANY($1::text[])
        AND ($4::text IS NULL OR td.day_of_week = $4)
        AND ($5::text IS NULL OR td.meal = $5)
        AND (
          $2 = ''
          OR LOWER(td.dining_hall) LIKE $3
          OR LOWER(td.item_name) LIKE $3
          OR LOWER(COALESCE(td.zone, '')) LIKE $3
        )
      GROUP BY LOWER(td.dining_hall), td.item_name
    )
    SELECT hall_key, item_name, protein_g, calories, source_url
    FROM normalized
    ORDER BY protein_g DESC, item_name ASC;
    """

    hall_keys = list(HALL_COORDS.keys())

    pool = await _ensure_pool()
    async with pool.acquire() as connection:
        records = await connection.fetch(
            sql,
            hall_keys,
            keyword_clean,
            like_pattern,
            day_of_week,
            meal_filter,
        )

    output: list[dict] = []
    for record in records:
        hall_key = record["hall_key"]
        hall_meta = HALL_COORDS[hall_key]
        output.append(
            {
                "venue_id": hall_key,
                "venue_name": hall_meta["venue_name"],
                "venue_category": hall_meta["venue_category"],
                "venue_lat": hall_meta["venue_lat"],
                "venue_lng": hall_meta["venue_lng"],
                "item_name": record["item_name"],
                "protein_grams": float(record["protein_g"]),
                "calories": (
                    float(record["calories"]) if record["calories"] is not None else None
                ),
                "hours_url": record["source_url"] or HALL_HOURS_URLS.get(hall_key),
                "tags": [],
            }
        )

    return output
