"""
schemas/
--------
Pydantic models define the shape of data coming IN (request bodies)
and going OUT (response JSON).

They are separate from SQLAlchemy models on purpose:
  - SQLAlchemy models talk to the database.
  - Pydantic schemas talk to the API clients.

This separation means we can expose only what we want (e.g. never
send hashed_password in a response) and validate input strictly
before it touches the database.
"""

from __future__ import annotations
from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, EmailStr


# ── Auth ──────────────────────────────────────────────────────────────────────

class RegisterRequest(BaseModel):
    name: str
    email: EmailStr
    password: str
    role: str                    # "hr" or "candidate"


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserOut                # included so the frontend gets user info immediately


class UserOut(BaseModel):
    id: str
    name: str
    email: str
    role: str
    created_at: datetime

    class Config:
        from_attributes = True  # allows constructing from SQLAlchemy model instances


# Fix forward reference (TokenResponse references UserOut defined after it)
TokenResponse.model_rebuild()


# ── Jobs ──────────────────────────────────────────────────────────────────────

class JobCreate(BaseModel):
    title: str
    department: Optional[str] = None
    location: Optional[str] = "Remote"
    job_type: Optional[str] = "Full-time"
    description: Optional[str] = None
    skills: Optional[List[str]] = []
    last_date: Optional[str] = None
    interview_date: Optional[str] = None


class JobUpdate(JobCreate):
    # Same fields as JobCreate — all optional for partial updates
    title: Optional[str] = None


class JobOut(BaseModel):
    id: str
    title: str
    department: Optional[str]
    location: Optional[str]
    job_type: Optional[str]
    description: Optional[str]
    skills: Optional[List[str]]
    last_date: Optional[str]
    interview_date: Optional[str]
    is_active: bool
    created_at: datetime
    hr_id: str
    hr_name: str = ""            # computed in the router, not stored in DB
    applicant_count: int = 0     # computed in the router
    shortlisted_count: int = 0

    class Config:
        from_attributes = True


# ── Applications ──────────────────────────────────────────────────────────────

class ApplyRequest(BaseModel):
    resume_text: Optional[str] = None
    resume_skills: Optional[List[str]] = []


class AnswerItem(BaseModel):
    question_text: str
    answer_text: Optional[str] = ""
    question_index: int


class SubmitInterviewRequest(BaseModel):
    answers: List[AnswerItem]
    # Scores sent from the frontend (still mocked for now; Phase 2 will compute these server-side)
    score_overall: Optional[float] = None
    score_relevance: Optional[float] = None
    score_confidence: Optional[float] = None
    score_emotion: Optional[float] = None
    score_communication: Optional[float] = None
    # Integrity
    violations_count: Optional[int] = 0
    disqualified: Optional[bool] = False


class ApplicationOut(BaseModel):
    id: str
    status: str
    applied_at: datetime
    resume_skills: Optional[List[str]]
    resume_text: Optional[str]
    score_overall: Optional[float]
    score_relevance: Optional[float]
    score_confidence: Optional[float]
    score_emotion: Optional[float]
    score_communication: Optional[float]
    violations_count: Optional[float] = 0
    disqualified: Optional[bool] = False
    candidate_id: str
    candidate_name: str = ""     # populated in the router
    job_id: str
    job_title: str = ""          # populated in the router

    class Config:
        from_attributes = True
