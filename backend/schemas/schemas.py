"""
schemas/schemas.py
------------------
Pydantic models for request validation and response serialisation.
"""

from __future__ import annotations
from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, EmailStr


# ── Auth ──────────────────────────────────────────────────────────────────────

class RegisterRequest(BaseModel):
    name:     str
    email:    EmailStr
    password: str
    role:     str              # "hr" or "candidate"
    company:  Optional[str] = None   # HR only; ignored for candidates


class LoginRequest(BaseModel):
    email:    EmailStr
    password: str


class UpdateProfileRequest(BaseModel):
    name:    Optional[str] = None
    company: Optional[str] = None


class TokenResponse(BaseModel):
    access_token: str
    token_type:   str = "bearer"
    user:         UserOut


class UserOut(BaseModel):
    id:         str
    name:       str
    email:      str
    role:       str
    company:    Optional[str] = None
    created_at: datetime

    class Config:
        from_attributes = True


TokenResponse.model_rebuild()


# ── Jobs ──────────────────────────────────────────────────────────────────────

class JobCreate(BaseModel):
    title:          str
    department:     Optional[str] = None
    location:       Optional[str] = "Remote"
    job_type:       Optional[str] = "Full-time"
    description:    Optional[str] = None
    skills:         Optional[List[str]] = []
    last_date:      Optional[str] = None
    interview_date: Optional[str] = None


class JobUpdate(JobCreate):
    title: Optional[str] = None


class JobOut(BaseModel):
    id:             str
    title:          str
    department:     Optional[str]
    location:       Optional[str]
    job_type:       Optional[str]
    description:    Optional[str]
    skills:         Optional[List[str]]
    last_date:      Optional[str]
    interview_date: Optional[str]
    is_active:      bool
    created_at:     datetime
    hr_id:          str
    hr_name:        str = ""
    hr_company:     str = ""       # ← company name shown on job card
    applicant_count:    int = 0
    shortlisted_count:  int = 0

    class Config:
        from_attributes = True


# ── Applications ──────────────────────────────────────────────────────────────

class ApplyRequest(BaseModel):
    resume_text:   Optional[str]       = None
    resume_skills: Optional[List[str]] = []


class AnswerItem(BaseModel):
    question_text:  str
    answer_text:    Optional[str] = ""
    question_index: int


class SubmitInterviewRequest(BaseModel):
    answers:             List[AnswerItem]
    score_overall:       Optional[float] = None
    score_relevance:     Optional[float] = None
    score_confidence:    Optional[float] = None
    score_emotion:       Optional[float] = None
    score_communication: Optional[float] = None
    violations_count:    Optional[int]   = 0
    disqualified:        Optional[bool]  = False


class ApplicationOut(BaseModel):
    id:                  str
    status:              str
    applied_at:          datetime
    resume_skills:       Optional[List[str]]
    resume_text:         Optional[str]
    score_overall:       Optional[float]
    score_relevance:     Optional[float]
    score_confidence:    Optional[float]
    score_emotion:       Optional[float]
    score_communication: Optional[float]
    violations_count:    Optional[float] = 0
    disqualified:        Optional[bool]  = False
    candidate_id:        str
    candidate_name:      str = ""
    job_id:              str
    job_title:           str = ""

    class Config:
        from_attributes = True


# ── Interview detail (answers + feedback) ─────────────────────────────────────

class AnswerOut(BaseModel):
    question_text:  str
    answer_text:    Optional[str]
    question_index: int

    class Config:
        from_attributes = True


class FeedbackItem(BaseModel):
    category: str     # "Relevance" | "Confidence" | "Emotion" | "Communication"
    score:    int
    label:    str     # "Excellent" | "Good" | "Needs Improvement"
    tip:      str     # actionable advice


class InterviewDetailOut(BaseModel):
    application:  ApplicationOut
    answers:      List[AnswerOut]
    feedback:     List[FeedbackItem]
    summary:      str          # one-paragraph overall summary


# ── Admin ─────────────────────────────────────────────────────────────────────

class AdminStatsOut(BaseModel):
    total_users:        int
    total_hr:           int
    total_candidates:   int
    total_jobs:         int
    active_jobs:        int
    total_applications: int
    shortlisted:        int
    disqualified:       int


class AdminUserOut(BaseModel):
    id:          str
    name:        str
    email:       str
    role:        str
    company:     Optional[str]
    created_at:  datetime
    job_count:   int = 0      # for HR
    app_count:   int = 0      # for candidates

    class Config:
        from_attributes = True


class AdminJobOut(BaseModel):
    id:               str
    title:            str
    department:       Optional[str]
    location:         Optional[str]
    job_type:         Optional[str]
    is_active:        bool
    created_at:       datetime
    hr_name:          str
    hr_company:       str
    applicant_count:  int
    shortlisted_count: int

    class Config:
        from_attributes = True