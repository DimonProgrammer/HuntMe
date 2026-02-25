from datetime import datetime
from typing import Optional

from sqlalchemy import BigInteger, Boolean, DateTime, Integer, String, Text, func
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    pass


class Candidate(Base):
    __tablename__ = "candidates"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    tg_user_id: Mapped[int] = mapped_column(BigInteger, unique=True, nullable=True)
    tg_username: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    name: Mapped[str] = mapped_column(String(255))
    region: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    platform: Mapped[Optional[str]] = mapped_column(String(100), nullable=True, default="telegram")
    candidate_type: Mapped[str] = mapped_column(String(20))  # operator, model, agent

    # Qualification fields (from HuntMe official scripts)
    has_pc: Mapped[Optional[bool]] = mapped_column(Boolean, nullable=True)
    age: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    study_status: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    # Values: working, student_distance, student_inperson, neither
    english_level: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    pc_confidence: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    cpu_model: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    gpu_model: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    hardware_compatible: Mapped[Optional[bool]] = mapped_column(Boolean, nullable=True)
    internet_speed: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    start_date: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    contact_info: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)

    # Legacy fields (kept for backwards compatibility)
    experience: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    availability: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    expected_rate: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)

    # Agent-specific fields
    recruiting_experience: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    available_hours: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)

    # Model-specific fields
    platform_experience: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    preferred_schedule: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)

    # Screening results
    score: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    recommendation: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)  # PASS, MAYBE, REJECT
    status: Mapped[str] = mapped_column(String(30), default="new")
    # Statuses: new -> screened -> interview_invited -> active -> churned
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), onupdate=func.now())


class JobPosting(Base):
    __tablename__ = "job_postings"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    platform: Mapped[str] = mapped_column(String(100))
    region: Mapped[str] = mapped_column(String(50))
    title: Mapped[str] = mapped_column(String(255))
    content: Mapped[str] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String(30), default="active")  # active, expired, removed
    applications_count: Mapped[int] = mapped_column(Integer, default=0)
    url: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    posted_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
