from datetime import datetime
from datetime import timedelta
from typing import Any

from fastapi import HTTPException
from fastapi import Request
from jose import JWTError
from jose import jwt
from passlib.context import CryptContext

from backend.app.config import ACCESS_TOKEN_EXPIRE_MINUTES
from backend.app.config import COOKIE_NAME
from backend.app.config import COOKIE_SAMESITE
from backend.app.config import COOKIE_SECURE
from backend.app.config import JWT_ALGORITHM
from backend.app.config import JWT_SECRET
from backend.app.services.postgres_db import _ensure_pool

try:
    import asyncpg
except ImportError:  # pragma: no cover - handled at runtime
    asyncpg = None


# bcrypt has a strict 72-byte input limit; bcrypt_sha256 pre-hashes first
# so users can safely use longer passwords without truncation issues.
pwd_context = CryptContext(schemes=["bcrypt_sha256"], deprecated="auto")


CREATE_AUTH_SQL = """
CREATE TABLE IF NOT EXISTS users (
    id BIGSERIAL PRIMARY KEY,
    email TEXT NOT NULL UNIQUE,
    password_hash TEXT NOT NULL,
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ
);

CREATE INDEX IF NOT EXISTS idx_users_email ON users(email);
"""


def _ensure_jwt_config() -> None:
    if not JWT_SECRET:
        raise RuntimeError("JWT_SECRET is required for auth endpoints.")


async def ensure_auth_tables() -> None:
    pool = await _ensure_pool()
    async with pool.acquire() as connection:
        await connection.execute(CREATE_AUTH_SQL)


def hash_password(password: str) -> str:
    return pwd_context.hash(password)


def verify_password(plain_password: str, password_hash: str) -> bool:
    return pwd_context.verify(plain_password, password_hash)


def create_access_token(user_id: int) -> str:
    _ensure_jwt_config()
    expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    payload = {"sub": str(user_id), "exp": expire}
    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)


def set_auth_cookie(response: Any, token: str) -> None:
    response.set_cookie(
        key=COOKIE_NAME,
        value=token,
        httponly=True,
        secure=COOKIE_SECURE,
        samesite=COOKIE_SAMESITE,
        max_age=ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        path="/",
    )


def clear_auth_cookie(response: Any) -> None:
    response.delete_cookie(key=COOKIE_NAME, path="/")


async def register_user(email: str, password: str) -> dict:
    await ensure_auth_tables()
    if len(password) < 8:
        raise ValueError("password must be at least 8 characters")

    email_clean = email.strip().lower()
    password_hash = hash_password(password)

    pool = await _ensure_pool()
    try:
        async with pool.acquire() as connection:
            row = await connection.fetchrow(
                """
                INSERT INTO users(email, password_hash)
                VALUES($1, $2)
                RETURNING id, email, created_at
                """,
                email_clean,
                password_hash,
            )
    except Exception as error:
        # asyncpg UniqueViolationError when duplicate email
        if asyncpg is not None and isinstance(error, asyncpg.UniqueViolationError):
            raise ValueError("email is already registered") from error
        raise

    return {
        "id": row["id"],
        "email": row["email"],
        "created_at": row["created_at"].isoformat(),
    }


async def authenticate_user(email: str, password: str) -> dict | None:
    await ensure_auth_tables()
    email_clean = email.strip().lower()
    pool = await _ensure_pool()
    async with pool.acquire() as connection:
        row = await connection.fetchrow(
            """
            SELECT id, email, password_hash, is_active
            FROM users
            WHERE email = $1
            """,
            email_clean,
        )

    if not row:
        return None
    if not verify_password(password, row["password_hash"]):
        return None
    if not row["is_active"]:
        return None

    return {"id": row["id"], "email": row["email"], "is_active": row["is_active"]}


async def get_user_by_id(user_id: int) -> dict | None:
    await ensure_auth_tables()
    pool = await _ensure_pool()
    async with pool.acquire() as connection:
        row = await connection.fetchrow(
            """
            SELECT id, email, is_active, created_at
            FROM users
            WHERE id = $1
            """,
            user_id,
        )
    if not row:
        return None
    return {
        "id": row["id"],
        "email": row["email"],
        "is_active": row["is_active"],
        "created_at": row["created_at"].isoformat(),
    }


async def get_current_user_from_request(request: Request) -> dict:
    token = request.cookies.get(COOKIE_NAME)
    if not token:
        raise HTTPException(status_code=401, detail="Not authenticated")

    try:
        _ensure_jwt_config()
        payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
        user_id = int(payload.get("sub", "0"))
        if user_id <= 0:
            raise ValueError("invalid sub")
    except (JWTError, ValueError) as error:
        raise HTTPException(status_code=401, detail="Invalid auth token") from error

    user = await get_user_by_id(user_id)
    if not user:
        raise HTTPException(status_code=401, detail="User not found")
    if not user["is_active"]:
        raise HTTPException(status_code=401, detail="User is inactive")
    return user
