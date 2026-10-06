from pathlib import Path
import json
import hashlib
import hmac
import os
import secrets
import sqlite3
from datetime import datetime, timedelta, timezone
from typing import Any

from fastapi import Depends, FastAPI, Header, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field, field_validator

from models import (
    AgentContext,
    ChatHistoryItem,
    ChatReply,
    ChatRequest,
    CustomerContext,
    ProductCard,
)


BASE_DIR = Path(__file__).resolve().parents[1]
DATABASE_PATH = BASE_DIR / "data" / "campus_customs.db"
MEDIA_ROOT = BASE_DIR / "data"
PASSWORD_ITERATIONS = 600_000
RESET_PIN_MINUTES = 15

app = FastAPI(title="Campus Customs API", version="0.1.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)


class RegisterRequest(BaseModel):
    first_name: str = Field(min_length=1, max_length=80)
    last_name: str = Field(min_length=1, max_length=80)
    email: str = Field(min_length=3, max_length=254, pattern=r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
    password: str = Field(min_length=8, max_length=128)
    confirm_password: str = Field(min_length=8, max_length=128)

    @field_validator("first_name", "last_name")
    @classmethod
    def clean_name(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("Name is required")
        return value


class LoginRequest(BaseModel):
    email: str = Field(min_length=3, max_length=254, pattern=r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
    password: str = Field(min_length=1, max_length=128)


class ForgotPasswordRequest(BaseModel):
    email: str = Field(min_length=3, max_length=254, pattern=r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


class ResetPasswordRequest(BaseModel):
    email: str = Field(min_length=3, max_length=254, pattern=r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
    pin: str = Field(pattern=r"^\d{6}$")
    password: str = Field(min_length=8, max_length=128)
    confirm_password: str = Field(min_length=8, max_length=128)


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def hash_password(password: str, iterations: int = PASSWORD_ITERATIONS) -> str:
    salt = secrets.token_hex(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode(), salt.encode(), iterations)
    return f"pbkdf2_sha256${salt}${digest.hex()}${iterations}"


def verify_password(password: str, stored_hash: str) -> bool:
    try:
        parts = stored_hash.split("$")
        if len(parts) == 4:
            _, salt, expected, iterations_text = parts
            iterations = int(iterations_text)
        elif len(parts) == 3 and parts[0] == "pbkdf2_sha256":
            # Compatibility with the supplied HW4 seed database.
            _, salt, expected = parts
            iterations = 120_000
        else:
            return False
        actual = hashlib.pbkdf2_hmac(
            "sha256", password.encode(), salt.encode(), iterations
        ).hex()
        return hmac.compare_digest(actual, expected)
    except (ValueError, TypeError):
        return False


def hash_value(value: str) -> str:
    return hashlib.sha256(value.encode()).hexdigest()


def init_auth_tables() -> None:
    connection = get_connection()
    try:
        connection.executescript(
            """
            CREATE TABLE IF NOT EXISTS sessions (
                token_hash TEXT PRIMARY KEY,
                user_id INTEGER NOT NULL REFERENCES users(id),
                created_at TEXT NOT NULL,
                expires_at TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS password_reset_tokens (
                token_hash TEXT PRIMARY KEY,
                user_id INTEGER NOT NULL REFERENCES users(id),
                expires_at TEXT NOT NULL,
                used_at TEXT
            );
            """
        )
        connection.commit()
    finally:
        connection.close()


def public_user(row: sqlite3.Row) -> dict[str, Any]:
    return {
        "id": row["id"],
        "first_name": row["first_name"] or row["name"].split(" ")[0],
        "last_name": row["last_name"] or "",
        "name": row["name"],
        "email": row["email"],
    }


def create_session(connection: sqlite3.Connection, user_id: int) -> str:
    token = secrets.token_urlsafe(32)
    now = utc_now()
    connection.execute(
        "INSERT INTO sessions VALUES (?, ?, ?, ?)",
        (hash_value(token), user_id, now.isoformat(), (now + timedelta(days=7)).isoformat()),
    )
    connection.commit()
    return token


def current_user(authorization: str | None = Header(default=None)) -> sqlite3.Row:
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Please log in to continue")
    token_hash = hash_value(authorization.removeprefix("Bearer ").strip())
    connection = get_connection()
    try:
        row = connection.execute(
            """
            SELECT users.* FROM sessions JOIN users ON users.id = sessions.user_id
            WHERE sessions.token_hash = ? AND sessions.expires_at > ?
            """,
            (token_hash, utc_now().isoformat()),
        ).fetchone()
        if row is None:
            raise HTTPException(status_code=401, detail="Your session has expired")
        return row
    finally:
        connection.close()


def get_connection() -> sqlite3.Connection:
    if not DATABASE_PATH.exists():
        raise HTTPException(status_code=500, detail="Catalogue database is not available")
    connection = sqlite3.connect(DATABASE_PATH)
    connection.row_factory = sqlite3.Row
    return connection


init_auth_tables()


def parse_json_list(value: str | None) -> list[str]:
    if not value:
        return []
    try:
        parsed = json.loads(value)
        return parsed if isinstance(parsed, list) else []
    except json.JSONDecodeError:
        return []


@app.post("/api/auth/register", status_code=201)
def register(body: RegisterRequest) -> dict[str, Any]:
    if body.password != body.confirm_password:
        raise HTTPException(status_code=400, detail="Passwords do not match")
    email = str(body.email).lower().strip()
    connection = get_connection()
    try:
        if connection.execute("SELECT 1 FROM users WHERE email = ?", (email,)).fetchone():
            raise HTTPException(status_code=409, detail="An account with that email already exists")
        name = f"{body.first_name} {body.last_name}"
        cursor = connection.execute(
            "INSERT INTO users (name, email, password_hash, first_name, last_name) VALUES (?, ?, ?, ?, ?)",
            (name, email, hash_password(body.password), body.first_name, body.last_name),
        )
        user = connection.execute("SELECT * FROM users WHERE id = ?", (cursor.lastrowid,)).fetchone()
        token = create_session(connection, cursor.lastrowid)
        return {"token": token, "user": public_user(user)}
    finally:
        connection.close()


@app.post("/api/auth/login")
def login(body: LoginRequest) -> dict[str, Any]:
    email = str(body.email).lower().strip()
    connection = get_connection()
    try:
        user = connection.execute("SELECT * FROM users WHERE email = ?", (email,)).fetchone()
        if user is None or not verify_password(body.password, user["password_hash"]):
            raise HTTPException(status_code=401, detail="Email or password is incorrect")
        token = create_session(connection, user["id"])
        return {"token": token, "user": public_user(user)}
    finally:
        connection.close()


@app.get("/api/auth/me")
def me(user: sqlite3.Row = Depends(current_user)) -> dict[str, Any]:
    return {"user": public_user(user)}


@app.post("/api/auth/logout")
def logout(authorization: str | None = Header(default=None)) -> dict[str, str]:
    if authorization and authorization.startswith("Bearer "):
        connection = get_connection()
        try:
            connection.execute(
                "DELETE FROM sessions WHERE token_hash = ?",
                (hash_value(authorization.removeprefix("Bearer ").strip()),),
            )
            connection.commit()
        finally:
            connection.close()
    return {"message": "Logged out"}


@app.post("/api/auth/forgot-password")
def forgot_password(body: ForgotPasswordRequest) -> dict[str, Any]:
    email = str(body.email).lower().strip()
    connection = get_connection()
    try:
        user = connection.execute("SELECT * FROM users WHERE email = ?", (email,)).fetchone()
        response: dict[str, Any] = {
            "message": "If an account exists for that email, a PIN has been sent."
        }
        if user is None:
            return response
        pin = f"{secrets.randbelow(1_000_000):06d}"
        expires = utc_now() + timedelta(minutes=RESET_PIN_MINUTES)
        connection.execute(
            "INSERT INTO password_reset_tokens VALUES (?, ?, ?, NULL)",
            (hash_value(pin), user["id"], expires.isoformat()),
        )
        connection.commit()
        # Email delivery is intentionally a later integration. Never return this in production.
        if os.getenv("APP_ENV", "development").lower() != "production":
            response["development_pin"] = pin
        return response
    finally:
        connection.close()


@app.post("/api/auth/reset-password")
def reset_password(body: ResetPasswordRequest) -> dict[str, str]:
    if body.password != body.confirm_password:
        raise HTTPException(status_code=400, detail="Passwords do not match")
    connection = get_connection()
    try:
        user = connection.execute(
            "SELECT * FROM users WHERE email = ?", (str(body.email).lower().strip(),)
        ).fetchone()
        if user is None:
            raise HTTPException(status_code=400, detail="The PIN or email is not valid")
        reset = connection.execute(
            """
            SELECT rowid FROM password_reset_tokens
            WHERE token_hash = ? AND user_id = ? AND used_at IS NULL AND expires_at > ?
            ORDER BY rowid DESC LIMIT 1
            """,
            (hash_value(body.pin), user["id"], utc_now().isoformat()),
        ).fetchone()
        if reset is None:
            raise HTTPException(status_code=400, detail="The PIN is invalid or has expired")
        connection.execute("UPDATE users SET password_hash = ? WHERE id = ?", (hash_password(body.password), user["id"]))
        connection.execute("UPDATE password_reset_tokens SET used_at = ? WHERE rowid = ?", (utc_now().isoformat(), reset["rowid"]))
        connection.execute("DELETE FROM sessions WHERE user_id = ?", (user["id"],))
        connection.commit()
        return {"message": "Password updated. You can now log in."}
    finally:
        connection.close()
def product_from_row(row: sqlite3.Row, connection: sqlite3.Connection) -> dict[str, Any]:
    product = dict(row)
    product["colors"] = parse_json_list(product.get("colors"))
    product["search_tags"] = parse_json_list(product.get("search_tags"))
    product["image_url"] = f"/media/products_white/{Path(product['image_file_path']).name}"
    inventory_rows = connection.execute(
        "SELECT size, quantity FROM inventory WHERE product_id = ? ORDER BY id",
        (product["product_id"],),
    ).fetchall()
    product["inventory"] = [dict(item) for item in inventory_rows]
    product["total_stock"] = sum(item["quantity"] for item in product["inventory"])
    return product


@app.get("/api/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/api/chat")
async def chat(body: ChatRequest, authorization: str | None = Header(default=None)) -> ChatReply:
    """Run one website chat turn through the Pydantic AI shopping agent."""
    try:
        from agent import run_chat

        user = current_user(authorization) if authorization else None
        result = await run_chat(
            body.message,
            [message.model_dump() for message in body.history],
            AgentContext(
                customer=CustomerContext(
                    user_id=user["id"] if user else None,
                    name=user["name"] if user else None,
                    email=user["email"] if user else None,
                ),
                page=body.page_context,
            ),
        )
        if user:
            save_chat_message(user["id"], "user", body.message)
            save_chat_message(
                user["id"], "assistant", result.reply,
                json.dumps([product.model_dump(mode="json") for product in result.products]),
            )
        return result
    except (RuntimeError, ImportError) as error:
        raise HTTPException(status_code=503, detail=str(error)) from error
    except Exception as error:
        if type(error).__name__ == "UsageLimitExceeded":
            raise HTTPException(
                status_code=503,
                detail="I couldn't complete that request within the assistant's limits. Please try a shorter question.",
            ) from error
        raise


def save_chat_message(
    user_id: int, role: str, content: str, products_json: str | None = None
) -> None:
    connection = get_connection()
    try:
        connection.execute(
            "INSERT INTO chat_messages (user_id, role, content, products_json) VALUES (?, ?, ?, ?)",
            (user_id, role, content, products_json),
        )
        connection.commit()
    finally:
        connection.close()


@app.get("/api/chat/history", response_model=list[ChatHistoryItem])
def chat_history(user: sqlite3.Row = Depends(current_user)) -> list[ChatHistoryItem]:
    """Return only the signed-in customer's own chat history."""
    connection = get_connection()
    try:
        rows = connection.execute(
            """
            SELECT role, content, products_json, created_at
            FROM chat_messages WHERE user_id = ? ORDER BY id DESC LIMIT 50
            """,
            (user["id"],),
        ).fetchall()
    finally:
        connection.close()
    history: list[ChatHistoryItem] = []
    for row in reversed(rows):
        products: list[ProductCard] = []
        if row["products_json"]:
            try:
                products = [ProductCard.model_validate(item) for item in json.loads(row["products_json"])]
            except (json.JSONDecodeError, TypeError, ValueError):
                products = []
        history.append(ChatHistoryItem(
            role=row["role"], content=row["content"], products=products, created_at=row["created_at"]
        ))
    return history


@app.get("/api/products")
def list_products(
    search: str | None = Query(default=None, max_length=100),
    limit: int = Query(default=102, ge=1, le=200),
) -> list[dict[str, Any]]:
    connection = get_connection()
    try:
        if search:
            term = f"%{search.strip()}%"
            rows = connection.execute(
                """
                SELECT * FROM catalogue
                WHERE name LIKE ? OR garment_type LIKE ? OR description LIKE ?
                   OR colors LIKE ? OR search_tags LIKE ?
                ORDER BY name LIMIT ?
                """,
                (term, term, term, term, term, limit),
            ).fetchall()
        else:
            rows = connection.execute(
                "SELECT * FROM catalogue ORDER BY name LIMIT ?", (limit,)
            ).fetchall()
        return [product_from_row(row, connection) for row in rows]
    finally:
        connection.close()


@app.get("/api/products/{product_id}")
def get_product(product_id: str) -> dict[str, Any]:
    connection = get_connection()
    try:
        row = connection.execute(
            "SELECT * FROM catalogue WHERE product_id = ?", (product_id,)
        ).fetchone()
        if row is None:
            raise HTTPException(status_code=404, detail="Product not found")
        return product_from_row(row, connection)
    finally:
        connection.close()


@app.get("/media/{file_path:path}")
def product_image(file_path: str) -> FileResponse:
    requested = (MEDIA_ROOT / file_path).resolve()
    if MEDIA_ROOT.resolve() not in requested.parents:
        raise HTTPException(status_code=400, detail="Invalid media path")
    if not requested.is_file():
        raise HTTPException(status_code=404, detail="Image not found")
    return FileResponse(requested)
