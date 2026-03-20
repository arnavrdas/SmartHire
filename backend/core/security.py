"""
core/security.py
----------------
Two responsibilities:
  1. Password hashing — we use bcrypt directly (no passlib).
     A hash is a one-way transformation: "password123" → "$2b$12$..."
     We never store or compare plain-text passwords.

  2. JWT tokens — JSON Web Tokens are signed strings that prove identity.
     The server creates a token on login; the client sends it with every
     subsequent request in the Authorization header.
"""

from datetime import datetime, timedelta

import bcrypt
from jose import jwt

from core.config import settings


# ── Password helpers ──────────────────────────────────────────────────────────

def hash_password(plain: str) -> str:
    """Turn a plain-text password into a bcrypt hash string."""
    # bcrypt.hashpw expects bytes, and returns bytes.
    # We decode to str so we can store it as a normal text column.
    pwd_bytes = plain.encode("utf-8")
    salt = bcrypt.gensalt()
    return bcrypt.hashpw(pwd_bytes, salt).decode("utf-8")


def verify_password(plain: str, hashed: str) -> bool:
    """Return True if the plain password matches the stored hash."""
    return bcrypt.checkpw(plain.encode("utf-8"), hashed.encode("utf-8"))


# ── JWT helpers ───────────────────────────────────────────────────────────────

def create_access_token(data: dict) -> str:
    """
    Create a signed JWT containing `data` plus an expiry time.
    The token is a base64-encoded string safe to send over HTTP.
    """
    payload = data.copy()
    expire = datetime.utcnow() + timedelta(
        minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES
    )
    payload["exp"] = expire
    return jwt.encode(payload, settings.SECRET_KEY, algorithm=settings.ALGORITHM)


def decode_access_token(token: str) -> dict | None:
    """
    Decode and verify a JWT.
    Returns the payload dict, or None if the token is invalid/expired.
    """
    try:
        return jwt.decode(
            token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM]
        )
    except Exception:
        return None
