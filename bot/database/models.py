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
    language: Mapped[Optional[str]] = mapped_column(String(5), nullable=True, default="en")
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

    # Referral tracking
    referrer_tg_id: Mapped[Optional[int]] = mapped_column(BigInteger, nullable=True)
    utm_source: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)

    # Screening results
    score: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    recommendation: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)  # PASS, MAYBE, REJECT
    status: Mapped[str] = mapped_column(String(30), default="new")
    # Statuses: new -> screened -> interview_invited -> active -> churned
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    # HuntMe CRM integration
    birth_date: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    phone_number: Mapped[Optional[str]] = mapped_column(String(30), nullable=True)
    phone_country: Mapped[Optional[str]] = mapped_column(String(5), nullable=True)
    huntme_crm_submitted: Mapped[Optional[bool]] = mapped_column(Boolean, nullable=True, default=False)
    huntme_crm_slot: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)

    interview_morning_sent: Mapped[Optional[bool]] = mapped_column(Boolean, nullable=True, default=False)
    interview_reminder_sent: Mapped[Optional[bool]] = mapped_column(Boolean, nullable=True, default=False)

    # Slot waiting queue
    waiting_for_slot: Mapped[Optional[bool]] = mapped_column(Boolean, nullable=True, default=False)
    slot_wait_since: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), onupdate=func.now())


class FunnelEvent(Base):
    """Tracks every step/action in the candidate funnel for analytics."""
    __tablename__ = "funnel_events"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    tg_user_id: Mapped[int] = mapped_column(BigInteger, index=True)
    event_type: Mapped[str] = mapped_column(String(50))
    # Types: step_entered, step_completed, question_asked, objection_detected,
    #        declined, completed, button_clicked, bot_started
    step_name: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    data: Mapped[Optional[str]] = mapped_column(Text, nullable=True)  # JSON extra info
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())


class FsmState(Base):
    """Persistent FSM storage — survives bot restarts."""
    __tablename__ = "fsm_states"

    chat_id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    user_id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    bot_id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    state: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    data: Mapped[Optional[str]] = mapped_column(Text, nullable=True, default="{}")
    updated_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), onupdate=func.now())


class SlotReservation(Base):
    """Temporary slot lock while candidate is in booking flow or pending admin approval.

    Expires after 30 min (cleaned up in _show_slots).
    Deleted on: admin approve, admin reject, rebook.
    """
    __tablename__ = "slot_reservations"

    slot_str: Mapped[str] = mapped_column(String(20), primary_key=True)
    tg_user_id: Mapped[int] = mapped_column(BigInteger, nullable=False)
    reserved_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())


class ChatwootMapping(Base):
    """Maps Telegram user IDs to Chatwoot contact + conversation IDs."""
    __tablename__ = "chatwoot_mappings"

    tg_user_id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    contact_id: Mapped[int] = mapped_column(Integer, nullable=False)
    conversation_id: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())


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
