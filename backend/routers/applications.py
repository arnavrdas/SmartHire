"""
routers/applications.py
-----------------------
POST /applications/{job_id}/apply      — candidate applies to a job
GET  /applications/mine                — candidate sees their own applications
GET  /applications/job/{job_id}        — HR sees all applicants for a job
POST /applications/{app_id}/interview  — candidate submits interview answers + scores
"""

from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from db.session import get_db
from db.models import Application, Job, InterviewAnswer, User
from core.deps import get_current_user, require_hr, require_candidate
from schemas.schemas import (
    ApplyRequest, SubmitInterviewRequest, ApplicationOut
)

router = APIRouter()


def _enrich_app(app: Application) -> ApplicationOut:
    """Add candidate name and job title to an application."""
    out = ApplicationOut.model_validate(app)
    out.candidate_name = app.candidate.name if app.candidate else ""
    out.job_title = app.job.title if app.job else ""
    return out


@router.post("/{job_id}/apply", response_model=ApplicationOut, status_code=201)
def apply(
    job_id: str,
    body: ApplyRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_candidate),
):
    """
    A candidate applies to a job.
    Prevents duplicate applications (one candidate → one job).
    """
    # Check the job exists
    job = db.query(Job).filter(Job.id == job_id, Job.is_active == True).first()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    # Prevent duplicate application
    existing = db.query(Application).filter(
        Application.candidate_id == current_user.id,
        Application.job_id == job_id,
    ).first()
    if existing:
        raise HTTPException(status_code=400, detail="You have already applied to this job")

    app = Application(
        candidate_id=current_user.id,
        job_id=job_id,
        resume_text=body.resume_text,
        resume_skills=body.resume_skills or [],
        status="interview_pending",
    )
    db.add(app)
    db.commit()
    db.refresh(app)
    return _enrich_app(app)


@router.get("/mine", response_model=List[ApplicationOut])
def my_applications(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_candidate),
):
    """Return all applications belonging to the logged-in candidate."""
    apps = (
        db.query(Application)
        .filter(Application.candidate_id == current_user.id)
        .order_by(Application.applied_at.desc())
        .all()
    )
    return [_enrich_app(a) for a in apps]


@router.get("/job/{job_id}", response_model=List[ApplicationOut])
def job_applicants(
    job_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_hr),
):
    """
    HR retrieves all applicants for one of their jobs.
    Enforces ownership: an HR can only see applicants for jobs they posted.
    """
    job = db.query(Job).filter(Job.id == job_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    if job.hr_id != current_user.id:
        raise HTTPException(status_code=403, detail="You don't own this job")

    apps = (
        db.query(Application)
        .filter(Application.job_id == job_id)
        .order_by(Application.applied_at.desc())
        .all()
    )
    return [_enrich_app(a) for a in apps]


@router.post("/{app_id}/interview", response_model=ApplicationOut)
def submit_interview(
    app_id: str,
    body: SubmitInterviewRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_candidate),
):
    """
    Candidate submits their interview answers and the AI scores
    computed on the frontend (Phase 1 — scores come from the client).
    In Phase 2 this endpoint will trigger a Celery task that computes
    scores server-side using Whisper + Librosa + DeepFace + NLP.
    """
    app = db.query(Application).filter(Application.id == app_id).first()
    if not app:
        raise HTTPException(status_code=404, detail="Application not found")
    if app.candidate_id != current_user.id:
        raise HTTPException(status_code=403, detail="This is not your application")
    if app.status in ("interviewed", "shortlisted", "disqualified"):
        raise HTTPException(status_code=400, detail="Interview already submitted")

    # Save each answer
    for item in body.answers:
        answer = InterviewAnswer(
            application_id=app.id,
            question_text=item.question_text,
            answer_text=item.answer_text,
            question_index=item.question_index,
        )
        db.add(answer)

    # Save scores
    app.score_overall       = body.score_overall
    app.score_relevance     = body.score_relevance
    app.score_confidence    = body.score_confidence
    app.score_emotion       = body.score_emotion
    app.score_communication = body.score_communication

    # Save integrity data
    app.violations_count = body.violations_count or 0
    app.disqualified     = body.disqualified or False

    # Update status
    if app.disqualified:
        app.status = "disqualified"
    elif body.score_overall and body.score_overall >= 72:
        app.status = "shortlisted"
    else:
        app.status = "interviewed"

    db.commit()
    db.refresh(app)
    return _enrich_app(app)
