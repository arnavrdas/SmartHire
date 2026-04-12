"""
routers/admin.py
----------------
GET /admin/stats     — platform-wide counts
GET /admin/users     — all users (HR + candidates)
GET /admin/jobs      — all job openings with applicant counts
"""

from typing import List

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from db.session import get_db
from db.models import User
from core.deps import get_current_user
from schemas.schemas import AdminStatsOut, AdminUserOut, AdminJobOut
from services.admin_service import get_stats, list_users, list_all_jobs

router = APIRouter(tags=["Admin"])


def require_admin(current_user: User = Depends(get_current_user)) -> User:
    if current_user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required",
        )
    return current_user


@router.get("/stats", response_model=AdminStatsOut)
def stats(
    db: Session = Depends(get_db),
    _: User = Depends(require_admin),
):
    return get_stats(db)


@router.get("/users", response_model=List[AdminUserOut])
def users(
    db: Session = Depends(get_db),
    _: User = Depends(require_admin),
):
    return list_users(db)


@router.get("/jobs", response_model=List[AdminJobOut])
def jobs(
    db: Session = Depends(get_db),
    _: User = Depends(require_admin),
):
    return list_all_jobs(db)