"""
routers/jobs.py
---------------
GET    /jobs           — list all active jobs (public, but richer if logged in)
GET    /jobs/{id}      — get one job
POST   /jobs           — create a job (HR only)
PUT    /jobs/{id}      — update a job (HR only, must own it)
DELETE /jobs/{id}      — deactivate a job (HR only, must own it)
"""

from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session

from db.session import get_db
from db.models import Job, Application, User
from core.deps import get_current_user, require_hr
from schemas.schemas import JobCreate, JobUpdate, JobOut

router = APIRouter()


def _enrich(job: Job, db: Session) -> JobOut:
    """
    Add computed fields (hr_name, applicant_count, shortlisted_count)
    that aren't stored directly on the Job row.
    """
    applicant_count = db.query(Application).filter(
        Application.job_id == job.id
    ).count()

    shortlisted_count = db.query(Application).filter(
        Application.job_id == job.id,
        Application.status == "shortlisted",
    ).count()

    out = JobOut.model_validate(job)
    out.hr_name = job.hr.name if job.hr else ""
    out.applicant_count = applicant_count
    out.shortlisted_count = shortlisted_count
    return out


@router.get("", response_model=List[JobOut])
def list_jobs(
    search: Optional[str] = Query(None),
    location: Optional[str] = Query(None),
    job_type: Optional[str] = Query(None),
    db: Session = Depends(get_db),
):
    """
    Return all active jobs.  Supports optional filtering by:
      ?search=React       — searches title and skills
      ?location=Remote
      ?job_type=Full-time
    """
    q = db.query(Job).filter(Job.is_active == True)

    if search:
        term = f"%{search.lower()}%"
        # ilike = case-insensitive LIKE in PostgreSQL
        q = q.filter(
            Job.title.ilike(term)
            # Note: filtering ARRAY columns by content requires a different approach
            # For now we search title only; skills search is done in the frontend
        )
    if location and location != "All":
        q = q.filter(Job.location == location)
    if job_type and job_type != "All":
        q = q.filter(Job.job_type == job_type)

    jobs = q.order_by(Job.created_at.desc()).all()
    return [_enrich(j, db) for j in jobs]


@router.get("/{job_id}", response_model=JobOut)
def get_job(job_id: str, db: Session = Depends(get_db)):
    job = db.query(Job).filter(Job.id == job_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    return _enrich(job, db)


@router.post("", response_model=JobOut, status_code=201)
def create_job(
    body: JobCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_hr),
):
    """Create a new job opening. Only HR users can do this."""
    job = Job(
        title=body.title,
        department=body.department,
        location=body.location,
        job_type=body.job_type,
        description=body.description,
        skills=body.skills or [],
        last_date=body.last_date,
        interview_date=body.interview_date,
        hr_id=current_user.id,
    )
    db.add(job)
    db.commit()
    db.refresh(job)
    return _enrich(job, db)


@router.put("/{job_id}", response_model=JobOut)
def update_job(
    job_id: str,
    body: JobUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_hr),
):
    """Update a job. The requesting HR must be the one who created it."""
    job = db.query(Job).filter(Job.id == job_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    if job.hr_id != current_user.id:
        raise HTTPException(status_code=403, detail="You don't own this job")

    # Update only the fields that were provided
    for field, value in body.model_dump(exclude_unset=True).items():
        setattr(job, field, value)

    db.commit()
    db.refresh(job)
    return _enrich(job, db)


@router.delete("/{job_id}", status_code=204)
def delete_job(
    job_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_hr),
):
    """Soft-delete: sets is_active=False so history is preserved."""
    job = db.query(Job).filter(Job.id == job_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    if job.hr_id != current_user.id:
        raise HTTPException(status_code=403, detail="You don't own this job")

    job.is_active = False
    db.commit()
