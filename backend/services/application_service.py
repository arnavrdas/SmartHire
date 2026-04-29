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


# ── Feedback generation ───────────────────────────────────────────────────────

def _score_label(score: float) -> str:
    if score >= 75: return "Excellent"
    if score >= 50: return "Good"
    return "Needs Improvement"


def _generate_feedback(app: Application):
    """
    Rule-based feedback — no external API, always works offline.
    Handles null scores gracefully by using 0 as fallback so feedback
    is always generated even when AI pipeline partially failed.
    """
    # Safely coerce null scores → 0 so we always have a number
    def _safe(v):
        try:
            return float(v) if v is not None else 0.0
        except (TypeError, ValueError):
            return 0.0

    scores = {
        "Relevance":     _safe(app.score_relevance),
        "Confidence":    _safe(app.score_confidence),
        "Emotion":       _safe(app.score_emotion),
        "Communication": _safe(app.score_communication),
    }

    tips = {
        "Relevance": {
            "Excellent":
                "Your answers were on-point and directly targeted each question. "
                "Keep using the STAR method (Situation, Task, Action, Result) to stay structured.",
            "Good":
                "Most answers addressed the question, but a few drifted off-topic. "
                "Before answering, identify the core keyword in the question and anchor your entire response to it.",
            "Needs Improvement":
                "Several answers did not directly address the questions asked. "
                "Practice active listening — repeat the question silently, pick one key idea, and build your answer only around that idea.",
        },
        "Confidence": {
            "Excellent":
                "Your voice was clear, well-projected, and showed minimal hesitation. "
                "Maintain this energy — steady pacing and projection signal confidence to any interviewer.",
            "Good":
                "Your delivery was mostly confident with occasional pauses. "
                "Try the 'pause with purpose' technique: a deliberate 1–2 second pause before answering sounds composed, not hesitant.",
            "Needs Improvement":
                "The audio analysis detected frequent long pauses and lower vocal energy. "
                "Record yourself answering mock interview questions daily, play it back, and consciously work on filling silences with speech rather than pauses.",
        },
        "Emotion": {
            "Excellent":
                "Your facial expressions were calm and composed throughout. "
                "Consistent eye contact and a relaxed brow signal confidence and engagement to the interviewer.",
            "Good":
                "Your expressions were mostly stable with occasional moments of visible tension. "
                "Try box breathing (4 counts in, hold 4, out 4) before each question to reset your baseline composure.",
            "Needs Improvement":
                "The analysis detected noticeable facial tension — frequent blinking and raised brows suggest anxiety. "
                "Practice mock interviews in front of a mirror or on video. Watching yourself helps you identify and correct nervous habits consciously.",
        },
        "Communication": {
            "Excellent":
                "Your speech was clear, well-paced, and articulate. "
                "High transcription quality indicates excellent enunciation — a major strength in any interview.",
            "Good":
                "Communication was mostly clear. Focus on eliminating filler words like 'um', 'uh', and 'like'. "
                "Replacing them with a brief pause sounds significantly more professional.",
            "Needs Improvement":
                "Speech clarity was lower than ideal, making transcription harder. "
                "Slow down by 20%, open your mouth more when speaking, and enunciate each syllable. "
                "Reading aloud for 10 minutes daily is a highly effective exercise.",
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

    # ── Summary paragraph ─────────────────────────────────────────────────────
    overall = _safe(app.score_overall)
    name    = app.candidate.name.split()[0] if app.candidate else "Candidate"

    if app.disqualified:
        summary = (
            f"{name}'s interview was terminated due to integrity violations detected by the anti-cheat system. "
            "No performance score has been assigned. We encourage fair and honest participation in future interviews."
        )
    elif overall >= 80:
        weakest = min(scores, key=scores.get)
        summary = (
            f"{name} delivered an outstanding interview, scoring {int(overall)}/100 overall. "
            f"Answers were highly relevant, delivery was confident, and communication was clear. "
            f"The one area to refine further is {weakest.lower()} — the tip below gives specific guidance."
        )
    elif overall >= 65:
        strengths  = [k for k, v in scores.items() if v >= 65]
        weaknesses = [k for k, v in scores.items() if v < 65]
        s_str = ", ".join(strengths).lower() if strengths else "several areas"
        w_str = (
            "Focus on improving " + ", ".join(weaknesses).lower() + " to cross the shortlisting threshold of 72."
            if weaknesses else "A strong, balanced performance overall."
        )
        summary = (
            f"{name} performed well, scoring {int(overall)}/100. "
            f"Clear strengths in {s_str}. {w_str}"
        )
    elif overall >= 40:
        summary = (
            f"{name} completed the interview with a score of {int(overall)}/100, "
            f"which is below the shortlisting threshold of 72. "
            "The feedback cards below highlight specific areas for improvement. "
            "With focused practice on the weakest dimensions, the score can improve significantly."
        )
    elif overall > 0:
        summary = (
            f"{name}'s interview score of {int(overall)}/100 indicates significant room for improvement. "
            "Review each feedback item carefully and prioritise consistent mock interview practice. "
            "Focusing on answer relevance and confident vocal delivery will produce the fastest gains."
        )
    else:
        # Scores are all 0 — AI pipeline likely failed or camera/mic was unavailable
        summary = (
            f"{name} completed the interview. The AI analysis pipeline encountered issues scoring this session "
            "(camera or microphone may have been unavailable). "
            "Answer content has been saved and can be reviewed below. "
            "Please re-attempt the interview with camera and microphone enabled for a full AI score."
        )

    return items, summary


def get_interview_detail(
    app_id: str, db: Session, current_user: User,
) -> InterviewDetailOut:
    app = db.query(Application).filter(Application.id == app_id).first()
    if not app:
        raise HTTPException(status_code=404, detail="Application not found")

    is_owner    = app.candidate_id == current_user.id
    is_hr_owner = current_user.role == "hr" and app.job and app.job.hr_id == current_user.id
    is_admin    = current_user.role == "admin"

    if not (is_owner or is_hr_owner or is_admin):
        raise HTTPException(status_code=403, detail="Access denied")

    if app.status not in ("interviewed", "shortlisted", "disqualified"):
        raise HTTPException(status_code=400, detail="Interview has not been completed yet")

    answers = [
        AnswerOut(
            question_text=a.question_text,
            answer_text=a.answer_text or "",
            question_index=int(a.question_index or 0),
        )
        for a in sorted(app.answers, key=lambda x: x.question_index or 0)
    ]

    feedback, summary = _generate_feedback(app)

    return InterviewDetailOut(
        application=_enrich_app(app),
        answers=answers,
        feedback=feedback,
        summary=summary,
    )