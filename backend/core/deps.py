"""
core/deps.py
------------
FastAPI dependencies shared across routers.

A "dependency" in FastAPI is just a function you declare as a parameter
with Depends(...).  FastAPI calls it automatically before your route runs.

get_current_user reads the Authorization header, validates the JWT,
looks up the user in the database, and injects the User object.
Any route that uses this dependency is automatically protected.
"""

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session

from core.security import decode_access_token
from db.session import get_db
from db.models import User

# This tells FastAPI that the token lives in the Authorization header
# as "Bearer <token>", and the login URL is /auth/login.
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")


def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db),
) -> User:
    """
    Decode the JWT, find the user, return them.
    Raises HTTP 401 if anything is wrong.
    """
    credentials_error = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )

    payload = decode_access_token(token)
    if payload is None:
        raise credentials_error

    user_id: str = payload.get("sub")
    if user_id is None:
        raise credentials_error

    user = db.query(User).filter(User.id == user_id).first()
    if user is None:
        raise credentials_error

    return user


def require_hr(current_user: User = Depends(get_current_user)) -> User:
    """Dependency that additionally enforces the HR role."""
    if current_user.role != "hr":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only HR accounts can perform this action",
        )
    return current_user


def require_candidate(current_user: User = Depends(get_current_user)) -> User:
    """Dependency that additionally enforces the candidate role."""
    if current_user.role != "candidate":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only candidate accounts can perform this action",
        )
    return current_user
