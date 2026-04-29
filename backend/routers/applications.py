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
    ApplyRequest, SubmitInterviewRequest, ApplicationOut,
    InterviewDetailOut, AnswerOut, FeedbackItem,
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


@router.get("/{app_id}/detail", response_model=InterviewDetailOut)
def interview_detail(
    app_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Return full interview details for a completed application.
    Accessible by the candidate who took the interview OR the HR who owns the job.
    """
    app = db.query(Application).filter(Application.id == app_id).first()
    if not app:
        raise HTTPException(status_code=404, detail="Application not found")

    # Access control: candidate can see their own, HR can see applicants for their jobs
    is_candidate_owner = (
        current_user.role == "candidate" and app.candidate_id == current_user.id
    )
    is_hr_owner = (
        current_user.role == "hr" and app.job and app.job.hr_id == current_user.id
    )
    if not (is_candidate_owner or is_hr_owner):
        raise HTTPException(status_code=403, detail="Access denied")

    # Answers (sorted by question index)
    answers_out = [
        AnswerOut(
            question_text=a.question_text,
            answer_text=a.answer_text,
            question_index=a.question_index,
        )
        for a in sorted(app.answers, key=lambda x: x.question_index)
    ]

    # Rule-based feedback (fallback shown when AI feedback is unavailable)
    def _score_label(s: float) -> str:
        if s >= 75:
            return "Excellent"
        if s >= 50:
            return "Good"
        return "Needs Work"

    def _score_tip(category: str, score: float) -> str:
        tips = {
            "Relevance": {
                "high": "Keep structuring your answers with the STAR method — it's clearly working well.",
                "mid":  "Try to be more direct: address the question first, then give supporting details.",
                "low":  "Practice answering mock questions and focus on directly addressing what's asked.",
            },
            "Confidence": {
                "high": "Your vocal energy is strong. Maintain this pacing in high-pressure situations.",
                "mid":  "Reduce filler words (um, uh) and add deliberate pauses instead of rushing.",
                "low":  "Practise speaking aloud daily; record yourself and listen back to build awareness.",
            },
            "Emotion": {
                "high": "Excellent composure — your calm demeanour projects trustworthiness.",
                "mid":  "Try to maintain relaxed facial muscles; brief breathing exercises before interviews help.",
                "low":  "Practise mock interviews on video to become comfortable with camera presence.",
            },
            "Communication": {
                "high": "Clear articulation and good pacing — keep it up.",
                "mid":  "Work on varying your tone; monotone delivery can reduce perceived clarity.",
                "low":  "Focus on speaking slowly and clearly; brevity with precision beats length.",
            },
        }
        bucket = "high" if score >= 75 else ("mid" if score >= 50 else "low")
        return tips.get(category, {}).get(bucket, "Keep practising to improve this area.")

    feedback_items: list[FeedbackItem] = []
    score_map = {
        "Relevance":     app.score_relevance,
        "Confidence":    app.score_confidence,
        "Emotion":       app.score_emotion,
        "Communication": app.score_communication,
    }
    for category, raw_score in score_map.items():
        score = round(raw_score or 0)
        feedback_items.append(FeedbackItem(
            category=category,
            score=score,
            label=_score_label(score),
            tip=_score_tip(category, score),
        ))

    # Overall summary
    overall = round(app.score_overall or 0)
    candidate_name = app.candidate.name if app.candidate else "The candidate"
    if app.disqualified:
        summary = (
            f"{candidate_name} was disqualified during the interview due to integrity violations. "
            "Scores reflect the answers recorded before disqualification."
        )
    elif overall >= 72:
        summary = (
            f"{candidate_name} performed strongly with an overall score of {overall}/100, "
            "exceeding the shortlisting threshold. Their answers demonstrated solid domain knowledge "
            "and communication skills."
        )
    else:
        summary = (
            f"{candidate_name} completed the interview with an overall score of {overall}/100. "
            "There is room for improvement — the detailed feedback below highlights specific areas to focus on."
        )

    return InterviewDetailOut(
        application=_enrich_app(app),
        answers=answers_out,
        feedback=feedback_items,
        summary=summary,
    )