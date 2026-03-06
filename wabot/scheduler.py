"""Follow-up & retention scheduler — APScheduler checks for silent leads
and sends milestone-based retention messages."""
import logging
from datetime import datetime, timedelta, timezone

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from sqlalchemy import select

from wabot.database import async_session
from wabot.models import WaLead

logger = logging.getLogger(__name__)

# Follow-up intervals in hours (index = followup_count)
FOLLOWUP_HOURS = [1, 24, 72]

scheduler = AsyncIOScheduler(timezone="UTC")


async def _check_silent_leads():
    """Check for leads that haven't responded and send follow-ups.

    Follow-up sequence:
        1h  — soft nudge
        24h — value message (Gabi story snippet)
        72h — last chance message
        After 72h with no response — mark as cold, stop messaging.
    """
    now = datetime.now(timezone.utc)
    async with async_session() as session:
        result = await session.execute(
            select(WaLead).where(
                WaLead.status == "active",
                WaLead.human_mode == False,  # noqa: E712
                WaLead.last_message_at.isnot(None),
                WaLead.followup_count < 3,
            )
        )
        leads = result.scalars().all()

    for lead in leads:
        if not lead.last_message_at:
            continue

        last = lead.last_message_at.replace(tzinfo=timezone.utc) if lead.last_message_at.tzinfo is None else lead.last_message_at
        hours_silent = (now - last).total_seconds() / 3600
        expected_followup = FOLLOWUP_HOURS[lead.followup_count] if lead.followup_count < len(FOLLOWUP_HOURS) else None

        if expected_followup and hours_silent >= expected_followup:
            from wabot.fsm import send_followup
            try:
                async with async_session() as session:
                    await send_followup(session, lead.phone)
                logger.info("Follow-up #%d sent to %s (silent %.1fh)", lead.followup_count + 1, lead.phone, hours_silent)
            except Exception as e:
                logger.error("Follow-up failed for %s: %s", lead.phone, e)


async def _check_retention_milestones():
    """Check for booked/approved leads that need retention messages.

    Milestones:
        - Day 1 after interview: check-in
        - Days 1-5 of working: daily motivational
        - Day 7 (shift 7): congratulations
    """
    now = datetime.now(timezone.utc)
    async with async_session() as session:
        # 1. Post-interview check-in (1 day after interview_date)
        result = await session.execute(
            select(WaLead).where(
                WaLead.status.in_(["booked", "approved"]),
                WaLead.human_mode == False,  # noqa: E712
                WaLead.interview_date.isnot(None),
                WaLead.retention_day < 1,
            )
        )
        leads_interview = result.scalars().all()

    for lead in leads_interview:
        interview_dt = lead.interview_date
        if interview_dt.tzinfo is None:
            interview_dt = interview_dt.replace(tzinfo=timezone.utc)
        hours_since = (now - interview_dt).total_seconds() / 3600
        if hours_since >= 24:
            from wabot.fsm import send_retention_message
            try:
                async with async_session() as session:
                    await send_retention_message(session, lead.phone, "post_interview")
                logger.info("Retention post-interview sent to %s", lead.phone)
            except Exception as e:
                logger.error("Retention post-interview failed for %s: %s", lead.phone, e)

    # 2. Daily motivation for working models (days 1-5)
    async with async_session() as session:
        result = await session.execute(
            select(WaLead).where(
                WaLead.status == "approved",
                WaLead.human_mode == False,  # noqa: E712
                WaLead.retention_day < 5,
                WaLead.shifts_completed >= 1,
            )
        )
        working_leads = result.scalars().all()

    for lead in working_leads:
        next_day = lead.retention_day + 1
        if next_day <= lead.shifts_completed and next_day <= 5:
            from wabot.fsm import send_retention_message
            try:
                async with async_session() as session:
                    await send_retention_message(session, lead.phone, f"work_day_{next_day}")
                logger.info("Retention day %d sent to %s", next_day, lead.phone)
            except Exception as e:
                logger.error("Retention day %d failed for %s: %s", next_day, lead.phone, e)

    # 3. 7-shift milestone
    async with async_session() as session:
        result = await session.execute(
            select(WaLead).where(
                WaLead.status == "approved",
                WaLead.human_mode == False,  # noqa: E712
                WaLead.shifts_completed >= 7,
                WaLead.retention_day < 7,
            )
        )
        milestone_leads = result.scalars().all()

    for lead in milestone_leads:
        from wabot.fsm import send_retention_message
        try:
            async with async_session() as session:
                await send_retention_message(session, lead.phone, "shift_7")
            logger.info("Retention 7-shift milestone sent to %s", lead.phone)
        except Exception as e:
            logger.error("Retention 7-shift failed for %s: %s", lead.phone, e)


def start():
    # Follow-up check every 15 minutes
    scheduler.add_job(
        _check_silent_leads,
        "interval",
        minutes=15,
        id="followup_check",
        replace_existing=True,
    )
    # Retention check every hour (less urgent than follow-ups)
    scheduler.add_job(
        _check_retention_milestones,
        "interval",
        minutes=60,
        id="retention_check",
        replace_existing=True,
    )
    scheduler.start()
    logger.info("Scheduler started: follow-up (15min) + retention (60min)")


def stop():
    scheduler.shutdown()
