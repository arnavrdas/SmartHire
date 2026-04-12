"""
db/models.py
------------
SQLAlchemy ORM models.  Each class = one database table.
"""

import uuid
from datetime import datetime

from sqlalchemy import (
    Column, String, Text, Boolean,
    DateTime, Float, ForeignKey, ARRAY
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from db.session import Base


def new_uuid():
    return str(uuid.uuid4())


# ── Users ─────────────────────────────────────────────────────────────────────
class User(Base):
    __tablename__ = "users"

    id              = Column(UUID(as_uuid=False), primary_key=True, default=new_uuid)
    name            = Column(String(120), nullable=False)
    email           = Column(String(255), unique=True, nullable=False, index=True)
    hashed_password = Column(String(255), nullable=False)
    role            = Column(String(20),  nullable=False)   # "hr", "candidate", "admin"
    # Company name — only meaningful for HR accounts, optional for candidates
    company         = Column(String(200), nullable=True)
    created_at      = Column(DateTime, default=datetime.utcnow)

    jobs         = relationship("Job",         back_populates="hr")
    applications = relationship("Application", back_populates="candidate")


# ── Jobs ──────────────────────────────────────────────────────────────────────
class Job(Base):
    __tablename__ = "jobs"

    id             = Column(UUID(as_uuid=False), primary_key=True, default=new_uuid)
    title          = Column(String(200), nullable=False)
    department     = Column(String(100))
    location       = Column(String(100))
    job_type       = Column(String(50))
    description    = Column(Text)
    skills         = Column(ARRAY(String), default=[])
    last_date      = Column(String(20))
    interview_date = Column(String(20))
    is_active      = Column(Boolean, default=True)
    created_at     = Column(DateTime, default=datetime.utcnow)

    hr_id = Column(UUID(as_uuid=False), ForeignKey("users.id"), nullable=False)
    hr    = relationship("User", back_populates="jobs")

    applications = relationship("Application", back_populates="job")


# ── Applications ──────────────────────────────────────────────────────────────
class Application(Base):
    __tablename__ = "applications"

    id             = Column(UUID(as_uuid=False), primary_key=True, default=new_uuid)
    resume_text    = Column(Text)
    resume_skills  = Column(ARRAY(String), default=[])
    status         = Column(String(30), default="applied")
    applied_at     = Column(DateTime, default=datetime.utcnow)

    # AI scores — null until interview is completed
    score_overall       = Column(Float, nullable=True)
    score_relevance     = Column(Float, nullable=True)
    score_confidence    = Column(Float, nullable=True)
    score_emotion       = Column(Float, nullable=True)
    score_communication = Column(Float, nullable=True)

    # Integrity
    violations_count = Column(Float,   default=0)
    disqualified     = Column(Boolean, default=False)

    # Foreign keys
    candidate_id = Column(UUID(as_uuid=False), ForeignKey("users.id"), nullable=False)
    job_id       = Column(UUID(as_uuid=False), ForeignKey("jobs.id"),  nullable=False)

    candidate = relationship("User", back_populates="applications")
    job       = relationship("Job",  back_populates="applications")
    answers   = relationship("InterviewAnswer", back_populates="application",
                             order_by="InterviewAnswer.question_index")


# ── Interview Answers ─────────────────────────────────────────────────────────
class InterviewAnswer(Base):
    __tablename__ = "interview_answers"

    id             = Column(UUID(as_uuid=False), primary_key=True, default=new_uuid)
    question_text  = Column(Text, nullable=False)
    answer_text    = Column(Text)
    question_index = Column(Float)
    created_at     = Column(DateTime, default=datetime.utcnow)

    application_id = Column(
        UUID(as_uuid=False), ForeignKey("applications.id"), nullable=False
    )
    application = relationship("Application", back_populates="answers")