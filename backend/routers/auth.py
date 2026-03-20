"""
routers/auth.py
---------------
POST /auth/register  — create a new account
POST /auth/login     — exchange email+password for a JWT
GET  /auth/me        — get the currently logged-in user
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from db.session import get_db
from db.models import User
from core.security import hash_password, verify_password, create_access_token
from core.deps import get_current_user
from schemas.schemas import RegisterRequest, LoginRequest, TokenResponse, UserOut

router = APIRouter()


@router.post("/register", response_model=TokenResponse, status_code=201)
def register(body: RegisterRequest, db: Session = Depends(get_db)):
    """
    Create a new user account.
    - Validates that the email isn't already taken.
    - Hashes the password before saving.
    - Returns a JWT immediately so the user is logged in right away.
    """
    # Check for duplicate email
    existing = db.query(User).filter(User.email == body.email).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="An account with this email already exists",
        )

    # Validate role
    if body.role not in ("hr", "candidate"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Role must be 'hr' or 'candidate'",
        )

    # Create the user row
    user = User(
        name=body.name,
        email=body.email,
        hashed_password=hash_password(body.password),
        role=body.role,
    )
    db.add(user)
    db.commit()
    db.refresh(user)  # refresh() populates auto-generated fields like id, created_at

    token = create_access_token({"sub": user.id})
    return TokenResponse(access_token=token, user=UserOut.model_validate(user))


@router.post("/login", response_model=TokenResponse)
def login(body: LoginRequest, db: Session = Depends(get_db)):
    """
    Verify email + password and return a JWT.
    We use the same generic error message for both "user not found"
    and "wrong password" — this prevents user enumeration attacks.
    """
    user = db.query(User).filter(User.email == body.email).first()

    if not user or not verify_password(body.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
        )

    token = create_access_token({"sub": user.id})
    return TokenResponse(access_token=token, user=UserOut.model_validate(user))


@router.get("/me", response_model=UserOut)
def me(current_user: User = Depends(get_current_user)):
    """Return the profile of the currently authenticated user."""
    return current_user
