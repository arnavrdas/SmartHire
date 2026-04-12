"""
services/admin_service.py
--------------------------
Admin-only queries: platform-wide stats, user list, job list.
All functions require the caller to have role="admin".
"""

from typing import List
from sqlalchemy.orm import Session

from db.models import User, Job, Application
from schemas.schemas import AdminStatsOut, AdminUserOut, AdminJobOut


def get_stats(db: Session) -> AdminStatsOut:
    total_users      = db.query(User).count()
    total_hr         = db.query(User).filter(User.role == "hr").count()
    total_candidates = db.query(User).filter(User.role == "candidate").count()
    total_jobs       = db.query(Job).count()
    active_jobs      = db.query(Job).filter(Job.is_active == True).count()
    total_apps       = db.query(Application).count()
    shortlisted      = db.query(Application).filter(Application.status == "shortlisted").count()
    disqualified     = db.query(Application).filter(Application.disqualified == True).count()

    return AdminStatsOut(
        total_users=total_users,
        total_hr=total_hr,
        total_candidates=total_candidates,
        total_jobs=total_jobs,
        active_jobs=active_jobs,
        total_applications=total_apps,
        shortlisted=shortlisted,
        disqualified=disqualified,
    )


def list_users(db: Session) -> List[AdminUserOut]:
    users = db.query(User).order_by(User.created_at.desc()).all()
    result = []
    for u in users:
        job_count = db.query(Job).filter(Job.hr_id == u.id).count()        if u.role == "hr"        else 0
        app_count = db.query(Application).filter(Application.candidate_id == u.id).count() if u.role == "candidate" else 0
        out = AdminUserOut.model_validate(u)
        out.job_count = job_count
        out.app_count = app_count
        result.append(out)
    return result


def list_all_jobs(db: Session) -> List[AdminJobOut]:
    jobs = db.query(Job).order_by(Job.created_at.desc()).all()
    result = []
    for j in jobs:
        app_count  = db.query(Application).filter(Application.job_id == j.id).count()
        short_count = db.query(Application).filter(
            Application.job_id == j.id, Application.status == "shortlisted"
        ).count()
        result.append(AdminJobOut(
            id=j.id,
            title=j.title,
            department=j.department,
            location=j.location,
            job_type=j.job_type,
            is_active=j.is_active,
            created_at=j.created_at,
            hr_name=j.hr.name    if j.hr else "",
            hr_company=j.hr.company if (j.hr and j.hr.company) else "",
            applicant_count=app_count,
            shortlisted_count=short_count,
        ))
    return result