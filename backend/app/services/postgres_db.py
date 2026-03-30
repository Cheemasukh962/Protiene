import asyncio
from typing import Any

from backend.app.config import POSTGRES_DSN

try:
    import asyncpg
except ImportError:  # pragma: no cover - handled at runtime in environments without asyncpg
    asyncpg = None


_pool: Any = None
_initialized = False
_init_lock = asyncio.Lock()


SEED_VENUES = [
    ("Segundo Dining Commons", "Dining Hall", 38.54161, -121.75774),
    ("Tercero Dining Commons", "Dining Hall", 38.54453, -121.74989),
    ("Cuarto Dining Commons", "Dining Hall", 38.53595, -121.76145),
    ("Silo Market", "Market", 38.53840, -121.75273),
    ("Silo Food Trucks", "Food Trucks", 38.53855, -121.75290),
    ("Memorial Union Food Court", "Food Court", 38.54266, -121.74857),
]


SEED_MENU_ITEMS = [
    ("Silo Market", "Peet's Protein Smoothie", 16, ["smoothie", "protein", "drink"]),
    ("Silo Market", "Greek Yogurt Parfait", 14, ["yogurt", "breakfast"]),
    ("Silo Food Trucks", "Chicken Burrito", 32, ["burrito", "chicken"]),
    ("Memorial Union Food Court", "Turkey Sandwich", 22, ["sandwich", "turkey"]),
    ("Memorial Union Food Court", "Protein Box", 18, ["protein", "snack"]),
    ("Segundo Dining Commons", "Grilled Chicken Plate", 42, ["chicken", "high protein"]),
    ("Tercero Dining Commons", "Egg White Scramble", 24, ["eggs", "breakfast"]),
    ("Cuarto Dining Commons", "Tofu Stir Fry Bowl", 20, ["tofu", "bowl"]),
]


CREATE_TABLES_SQL = """
CREATE TABLE IF NOT EXISTS venues (
    id SERIAL PRIMARY KEY,
    name TEXT NOT NULL UNIQUE,
    category TEXT NOT NULL,
    lat DOUBLE PRECISION NOT NULL,
    lng DOUBLE PRECISION NOT NULL,
    active BOOLEAN NOT NULL DEFAULT TRUE
);

CREATE TABLE IF NOT EXISTS menu_items (
    id SERIAL PRIMARY KEY,
    venue_id INTEGER NOT NULL REFERENCES venues(id) ON DELETE CASCADE,
    name TEXT NOT NULL,
    protein_grams INTEGER NOT NULL CHECK (protein_grams >= 0),
    tags TEXT[] NOT NULL DEFAULT '{}',
    active BOOLEAN NOT NULL DEFAULT TRUE
);

CREATE INDEX IF NOT EXISTS idx_menu_items_venue_id ON menu_items(venue_id);
"""


async def _ensure_pool() -> Any:
    global _pool

    if asyncpg is None:
        raise RuntimeError("asyncpg is not installed. Install dependencies from requirements.txt.")
    if not POSTGRES_DSN:
        raise RuntimeError("POSTGRES_DSN is required to use recommendations.")

    if _pool is None:
        _pool = await asyncpg.create_pool(dsn=POSTGRES_DSN, min_size=1, max_size=5)
    return _pool


async def _seed_if_empty(connection: Any) -> None:
    venue_count = await connection.fetchval("SELECT COUNT(*) FROM venues")
    if venue_count and venue_count > 0:
        return

    for name, category, lat, lng in SEED_VENUES:
        await connection.execute(
            "INSERT INTO venues(name, category, lat, lng) VALUES($1, $2, $3, $4)",
            name,
            category,
            lat,
            lng,
        )

    for venue_name, item_name, protein_grams, tags in SEED_MENU_ITEMS:
        venue_id = await connection.fetchval("SELECT id FROM venues WHERE name = $1", venue_name)
        await connection.execute(
            """
            INSERT INTO menu_items(venue_id, name, protein_grams, tags)
            VALUES($1, $2, $3, $4)
            """,
            venue_id,
            item_name,
            protein_grams,
            tags,
        )


async def ensure_db_initialized() -> None:
    global _initialized
    if _initialized:
        return

    async with _init_lock:
        if _initialized:
            return
        pool = await _ensure_pool()
        async with pool.acquire() as connection:
            await connection.execute(CREATE_TABLES_SQL)
            await _seed_if_empty(connection)
        _initialized = True


async def search_keyword_top_item_per_venue(keyword: str) -> list[dict]:
    await ensure_db_initialized()

    if not keyword.strip():
        return []

    like_pattern = f"%{keyword.lower()}%"
    sql = """
    SELECT DISTINCT ON (v.id)
      v.id AS venue_id,
      v.name AS venue_name,
      v.category AS venue_category,
      v.lat AS venue_lat,
      v.lng AS venue_lng,
      mi.id AS item_id,
      mi.name AS item_name,
      mi.protein_grams AS protein_grams,
      mi.tags AS tags
    FROM venues v
    JOIN menu_items mi ON mi.venue_id = v.id
    WHERE v.active = TRUE
      AND mi.active = TRUE
      AND (
          LOWER(v.name) LIKE $1
          OR LOWER(mi.name) LIKE $1
          OR EXISTS (
            SELECT 1 FROM unnest(mi.tags) AS t(tag)
            WHERE LOWER(tag) LIKE $1
          )
      )
    ORDER BY v.id, mi.protein_grams DESC, mi.id ASC;
    """

    pool = await _ensure_pool()
    async with pool.acquire() as connection:
        records = await connection.fetch(sql, like_pattern)

    return [dict(record) for record in records]
