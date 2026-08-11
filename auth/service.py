import re

from auth.dependencies import authenticate_user
from auth.security import hash_password
from auth.token import TokenError, create_access_token, create_refresh_token, decode_token
from database.connection import execute, fetch_one

EMAIL_RE = r"^[^@\s]+@[^@\s]+\.[^@\s]+$"


def register_user(name: str, email: str, password: str, role: str = "user") -> dict:
    name = name.strip()
    email = email.strip().lower()
    if not name:
        raise ValueError("Name is required")
    if not re.match(EMAIL_RE, email):
        raise ValueError("Invalid email format")
    if len(password) < 6:
        raise ValueError("Password must be at least 6 characters")
    if role not in ("user", "recruiter", "admin"):
        raise ValueError("Invalid role")

    existing = fetch_one("SELECT id FROM users WHERE email = %s", (email,))
    if existing:
        raise ValueError("Email already registered")

    password_hash = hash_password(password)
    user_id = execute(
        "INSERT INTO users (name, email, password_hash, role) VALUES (%s, %s, %s, %s)",
        (name, email, password_hash, role),
    )
    user = fetch_one(
        "SELECT id, name, email, role, is_active, avatar_url, created_at FROM users WHERE id = %s",
        (user_id,),
    )
    tokens = _issue_tokens(user)
    return {"user": user, **tokens}


def login_user(email: str, password: str) -> dict:
    user = authenticate_user(email.strip().lower(), password)
    if not user:
        raise ValueError("Invalid email or password")
    public_user = {k: v for k, v in user.items() if k != "password_hash"}
    tokens = _issue_tokens(public_user)
    return {"user": public_user, **tokens}


def refresh_access_token(refresh_token: str) -> dict:
    try:
        payload = decode_token(refresh_token)
    except TokenError as exc:
        raise ValueError(str(exc)) from exc
    if payload.get("type") != "refresh":
        raise ValueError("Invalid token type")

    user_id = int(payload.get("sub", "0"))
    user = fetch_one(
        "SELECT id, name, email, role, is_active, avatar_url, created_at FROM users WHERE id = %s",
        (user_id,),
    )
    if not user or not user["is_active"]:
        raise ValueError("User not found or inactive")
    return {"access_token": create_access_token(user["id"], user["role"]), "token_type": "bearer"}


def _issue_tokens(user: dict) -> dict:
    return {
        "access_token": create_access_token(user["id"], user["role"]),
        "refresh_token": create_refresh_token(user["id"]),
        "token_type": "bearer",
    }
