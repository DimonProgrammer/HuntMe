"""Follow-up scheduler — APScheduler checks for silent leads."""
import logging
from datetime import datetime, timedelta, timezone

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from sqlalchemy import select

from wabot.database import async_session
from wabot.models import WaLead

logger = logging.getLogger(__name__)

# Follow-up intervals
FOLLOWUP_HOURS = [1, 24, 72]

scheduler = AsyncIOScheduler(timezone="UTC")


async def _check_silent_leads():
    """Check for leads that haven't responded and send follow-ups."""
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
            async with async_session() as session:
                await send_followup(session, lead.phone)
            logger.info("Follow-up #%d sent to %s", lead.followup_count, lead.phone)


def start():
    scheduler.add_job(_check_silent_leads, "interval", minutes=15, id="followup_check")
    scheduler.start()
    logger.info("Follow-up scheduler started")


def stop():
    scheduler.shutdown()
