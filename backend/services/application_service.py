"""
services/application_service.py
--------------------------------
Business logic for applications, interview submission, interview detail, and feedback.
"""

from typing import List

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from db.models import Application, Job, InterviewAnswer, User
from schemas.schemas import (
    ApplyRequest, SubmitInterviewRequest, ApplicationOut,
    AnswerOut, FeedbackItem, InterviewDetailOut,
)


def _enrich_app(app: Application) -> ApplicationOut:
    out = ApplicationOut.model_validate(app)
    out.candidate_name = app.candidate.name if app.candidate else ""
    out.job_title      = app.job.title      if app.job      else ""
    return out


def apply_to_job(job_id: str, body: ApplyRequest, db: Session, current_user: User) -> ApplicationOut:
    job = db.query(Job).filter(Job.id == job_id, Job.is_active == True).first()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    existing = db.query(Application).filter(
        Application.candidate_id == current_user.id,
        Application.job_id == job_id,
    ).first()
    if existing:
        raise HTTPException(status_code=400, detail="You have already applied to this job")
    app = Application(
        candidate_id=current_user.id, job_id=job_id,
        resume_text=body.resume_text, resume_skills=body.resume_skills or [],
        status="interview_pending",
    )
    db.add(app); db.commit(); db.refresh(app)
    return _enrich_app(app)


def my_applications(db: Session, current_user: User) -> List[ApplicationOut]:
    apps = (
        db.query(Application)
        .filter(Application.candidate_id == current_user.id)
        .order_by(Application.applied_at.desc())
        .all()
    )
    return [_enrich_app(a) for a in apps]


def job_applicants(job_id: str, db: Session, current_user: User) -> List[ApplicationOut]:
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


def submit_interview(
    app_id: str, body: SubmitInterviewRequest,
    db: Session, current_user: User,
) -> ApplicationOut:
    app = db.query(Application).filter(Application.id == app_id).first()
    if not app:
        raise HTTPException(status_code=404, detail="Application not found")
    if app.candidate_id != current_user.id:
        raise HTTPException(status_code=403, detail="This is not your application")
    if app.status in ("interviewed", "shortlisted", "disqualified"):
        raise HTTPException(status_code=400, detail="Interview already submitted")

    for item in body.answers:
        db.add(InterviewAnswer(
            application_id=app.id,
            question_text=item.question_text,
            answer_text=item.answer_text,
            question_index=item.question_index,
        ))

    app.score_overall       = body.score_overall
    app.score_relevance     = body.score_relevance
    app.score_confidence    = body.score_confidence
    app.score_emotion       = body.score_emotion
    app.score_communication = body.score_communication
    app.violations_count    = body.violations_count or 0
    app.disqualified        = body.disqualified or False

    if app.disqualified:
        app.status = "disqualified"
    elif body.score_overall and body.score_overall >= 72:
        app.status = "shortlisted"
    else:
        app.status = "interviewed"

    db.commit(); db.refresh(app)
    return _enrich_app(app)


# ── Interview Detail (answers + AI feedback) ─────────────────────────────────

def _score_label(score: float) -> str:
    if score >= 75: return "Excellent"
    if score >= 55: return "Good"
    return "Needs Improvement"


def _generate_feedback(app: Application) -> tuple[List[FeedbackItem], str]:
    """
    Generate per-dimension feedback tips and an overall summary paragraph
    from the AI scores stored on the application.
    No external API call — purely rule-based so it always works offline.
    """
    scores = {
        "Relevance":     app.score_relevance     or 0,
        "Confidence":    app.score_confidence    or 0,
        "Emotion":       app.score_emotion       or 0,
        "Communication": app.score_communication or 0,
    }

    tips = {
        "Relevance": {
            "Excellent":         "Your answers were on-point and well-targeted to each question. Keep structuring answers with the STAR method (Situation, Task, Action, Result) for consistency.",
            "Good":              "Most answers addressed the question, but a few drifted off-topic. Before answering, take a breath and mentally map your response to the question's core topic.",
            "Needs Improvement": "Several answers did not directly address the questions asked. Practice identifying the keyword in each question and anchor your entire answer around it.",
        },
        "Confidence": {
            "Excellent":         "Your voice was clear, projected well, and showed minimal hesitation. Excellent delivery — maintain this energy in real interviews.",
            "Good":              "Your delivery was generally confident with occasional pauses. Try the 'pause with purpose' technique: pause briefly before answering, then speak at a steady pace.",
            "Needs Improvement": "The audio analysis detected frequent long pauses and lower vocal energy. Practice speaking aloud daily — record yourself answering common questions and review the playback.",
        },
        "Emotion": {
            "Excellent":         "Your facial expressions were calm and composed throughout the interview. You projected engagement and confidence visually.",
            "Good":              "Your expressions were mostly stable with occasional moments of visible tension. Deep breathing before each question can help maintain composure.",
            "Needs Improvement": "The analysis detected noticeable facial tension (rapid blinking, raised brows). Mock interviews in front of a mirror and mindfulness practice can help regulate nervous responses.",
        },
        "Communication": {
            "Excellent":         "Your speech was clear, articulate, and well-paced. The transcription quality was high, indicating excellent enunciation.",
            "Good":              "Communication was mostly clear. Focus on reducing filler words ('um', 'uh', 'like') — replacing them with a brief pause sounds more professional.",
            "Needs Improvement": "Speech clarity was lower than ideal. Practise speaking more slowly and enunciating each word. Recording yourself and listening back is highly effective.",
        },
    }

    items: List[FeedbackItem] = []
    for category, score in scores.items():
        label = _score_label(score)
        items.append(FeedbackItem(
            category=category,
            score=int(round(score)),
            label=label,
            tip=tips[category][label],
        ))

    # ── Overall summary ───────────────────────────────────────────────────────
    overall = app.score_overall or 0
    name    = app.candidate.name.split()[0] if app.candidate else "Candidate"

    if app.disqualified:
        summary = (
            f"{name}'s interview was terminated due to integrity violations. "
            "No performance assessment is available. We encourage honest participation "
            "in future interviews to receive a fair evaluation."
        )
    elif overall >= 80:
        weakest = min(scores, key=scores.get)
        summary = (
            f"{name} delivered an outstanding interview performance, scoring {int(overall)}/100 overall. "
            f"Answers were highly relevant, delivery was confident, and communication was clear. "
            f"The main area to refine further is {weakest.lower()} — see the tip below."
        )
    elif overall >= 65:
        strengths = [k for k, v in scores.items() if v >= 65]
        weaknesses = [k for k, v in scores.items() if v < 65]
        summary = (
            f"{name} performed well in this interview, scoring {int(overall)}/100. "
            f"Strengths include {', '.join(strengths).lower() if strengths else 'several areas'}. "
            f"{'Focus on improving ' + ', '.join(weaknesses).lower() + ' to reach the shortlisting threshold.' if weaknesses else 'A strong, balanced performance.'}"
        )
    elif overall >= 50:
        summary = (
            f"{name} completed the interview but the performance (score {int(overall)}/100) was below the shortlisting threshold of 72. "
            "The feedback below highlights specific areas to work on. With targeted practice, the score can improve significantly."
        )
    else:
        summary = (
            f"{name}'s interview score of {int(overall)}/100 suggests significant room for improvement. "
            "Review each feedback item carefully. Consistent mock interview practice, focusing on answer relevance and confident delivery, will make a meaningful difference."
        )

    return items, summary


def get_interview_detail(
    app_id: str, db: Session, current_user: User,
) -> InterviewDetailOut:
    """
    Return the full interview detail for a completed application.
    Access rules:
      - The candidate who owns the application can always see it.
      - The HR who posted the job can see it.
      - Admin can see anything.
    """
    app = db.query(Application).filter(Application.id == app_id).first()
    if not app:
        raise HTTPException(status_code=404, detail="Application not found")

    # Authorisation check
    is_owner    = app.candidate_id == current_user.id
    is_hr_owner = (current_user.role == "hr"    and app.job and app.job.hr_id == current_user.id)
    is_admin    = current_user.role == "admin"

    if not (is_owner or is_hr_owner or is_admin):
        raise HTTPException(status_code=403, detail="Access denied")

    if app.status not in ("interviewed", "shortlisted", "disqualified"):
        raise HTTPException(status_code=400, detail="Interview has not been completed yet")

    answers = [
        AnswerOut(
            question_text=a.question_text,
            answer_text=a.answer_text,
            question_index=int(a.question_index or 0),
        )
        for a in app.answers
    ]

    feedback, summary = _generate_feedback(app)

    return InterviewDetailOut(
        application=_enrich_app(app),
        answers=answers,
        feedback=feedback,
        summary=summary,
    )