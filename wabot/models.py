from datetime import datetime
from typing import Optional

from sqlalchemy import BigInteger, Boolean, DateTime, Integer, String, Text, func
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    pass


class WaLead(Base):
    """WhatsApp lead — one row per phone number."""
    __tablename__ = "wa_leads"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    phone: Mapped[str] = mapped_column(String(20), unique=True, nullable=False)  # +55...
    bitrix_id: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    name: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)

    # Funnel state
    step: Mapped[int] = mapped_column(Integer, default=0)
    state: Mapped[str] = mapped_column(Text, default="{}")  # JSON: collected data per step
    human_mode: Mapped[bool] = mapped_column(Boolean, default=False)  # True = bot silent

    # Lead data
    city: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    age: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    device: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)  # iOS/Android
    source: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)  # wa_ad/job_board/referral
    objections: Mapped[Optional[str]] = mapped_column(Text, nullable=True)  # collected objection texts

    # Status
    status: Mapped[str] = mapped_column(String(20), default="active")
    # active | qualified | booked | approved | rejected | paused | cold | agent

    # Role track: "model" (default) or "agent" (fallback)
    role: Mapped[str] = mapped_column(String(20), default="model")
    disqualify_reason: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)

    # HuntMe CRM
    huntme_slot: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    huntme_submitted: Mapped[bool] = mapped_column(Boolean, default=False)

    # Follow-up tracking
    last_message_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    followup_count: Mapped[int] = mapped_column(Integer, default=0)

    # Retention tracking (post-booking milestones)
    interview_date: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    shifts_completed: Mapped[int] = mapped_column(Integer, default=0)
    retention_day: Mapped[int] = mapped_column(Integer, default=0)  # last retention message sent (day number)

    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), onupdate=func.now())
