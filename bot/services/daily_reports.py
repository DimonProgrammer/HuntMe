"""Daily admin reports: morning briefing + evening summary.

Morning (10:00 +5): today's interviews, pending actions, pipeline.
Evening (22:00 +5): daily activity, funnel by offer, interview outcomes, totals.
"""

from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timedelta, timezone

from aiogram import Bot
from sqlalchemy import func, select, case, literal_column

from bot.config import config
from bot.database.connection import async_session
from bot.database.models import Candidate, FunnelEvent

logger = logging.getLogger(__name__)

_YEKATERINBURG = timezone(timedelta(hours=5))

_MORNING_HOUR = 10
_EVENING_HOUR = 22
_CHECK_INTERVAL = 60  # seconds


# ── helpers ──

def _status_icon(status: str, confirmed: str | None) -> str:
    if status == "interview_invited":
        if confirmed == "confirmed":
            return "\u2705"
        if confirmed == "cancelled":
            return "\ud83d\udeab"
        return "\u23f3 awaiting confirmation"
    if status == "pending_crm_approval":
        return "\u23f3 pending approval"
    return status


def _now_yek() -> datetime:
    return datetime.now(_YEKATERINBURG)


# ── morning report ──

async def _build_morning_report() -> str:
    now = _now_yek()
    today_str = now.strftime("%d.%m.%Y")
    date_display = now.strftime("%a %d %b %Y")

    async with async_session() as session:
        # Today's interviews
        interviews = (await session.execute(
            select(Candidate)
            .where(Candidate.huntme_crm_slot.like(f"{today_str}%"))
            .order_by(Candidate.huntme_crm_slot)
        )).scalars().all()

        # Pending actions
        pending = (await session.execute(
            select(
                Candidate.candidate_type,
                Candidate.status,
                func.count().label("cnt"),
            )
            .where(Candidate.status.in_(["screened", "pending_crm_approval"]))
            .group_by(Candidate.candidate_type, Candidate.status)
        )).all()

        waiting = (await session.execute(
            select(func.count())
            .where(Candidate.waiting_for_slot.is_(True))
        )).scalar() or 0

        # Pipeline by type
        pipeline = (await session.execute(
            select(
                Candidate.candidate_type,
                Candidate.status,
                func.count().label("cnt"),
            )
            .group_by(Candidate.candidate_type, Candidate.status)
        )).all()

    # Format interviews
    lines = [f"\u2600\ufe0f MORNING BRIEFING \u2014 {date_display}\n"]

    lines.append("\ud83d\udccb TODAY'S INTERVIEWS:")
    if interviews:
        for c in interviews:
            slot_time = c.huntme_crm_slot.split(" ")[1] if " " in c.huntme_crm_slot else c.huntme_crm_slot
            tg = f"@{c.tg_username}" if c.tg_username else "\u2014"
            icon = _status_icon(c.status, c.interview_confirmed)
            lines.append(f"  {slot_time} \u2014 {c.name} ({tg}) {icon}")
    else:
        lines.append("  No interviews today")

    # Pending actions
    screened_pass = sum(r.cnt for r in pending if r.status == "screened")
    pending_crm = sum(r.cnt for r in pending if r.status == "pending_crm_approval")
    has_pending = screened_pass or pending_crm or waiting

    if has_pending:
        lines.append("\n\u26a1 PENDING ACTIONS:")
        if screened_pass:
            lines.append(f"  \ud83d\udfe1 {screened_pass} candidates awaiting approval")
        if pending_crm:
            lines.append(f"  \ud83d\udd34 {pending_crm} pending CRM submission")
        if waiting:
            lines.append(f"  \u23f3 {waiting} waiting for interview slot")

    # Pipeline
    pipe_map: dict[str, dict[str, int]] = {}
    for r in pipeline:
        ct = r.candidate_type or "operator"
        pipe_map.setdefault(ct, {})
        pipe_map[ct][r.status] = r.cnt

    if pipe_map:
        lines.append("\n\ud83d\udcca PIPELINE:")
        for ct in ["operator", "model", "agent"]:
            if ct not in pipe_map:
                continue
            d = pipe_map[ct]
            total = sum(d.values())
            screened = d.get("screened", 0)
            invited = d.get("interview_invited", 0)
            applied = d.get("agent_applied", 0)
            parts = [f"{total} total"]
            if screened:
                parts.append(f"{screened} screened")
            if invited:
                parts.append(f"{invited} invited")
            if applied:
                parts.append(f"{applied} applied")
            label = ct.capitalize() + "s"
            lines.append(f"  {label}: {', '.join(parts)}")

    return "\n".join(lines)


# ── evening report ──

async def _build_evening_report() -> str:
    now = _now_yek()
    today_str = now.strftime("%d.%m.%Y")
    date_display = now.strftime("%a %d %b %Y")
    # Start of day in UTC for funnel_events (server_default=now() is UTC)
    day_start_utc = now.replace(hour=0, minute=0, second=0, microsecond=0) - timedelta(hours=5)

    async with async_session() as session:
        # Today's bot starts
        bot_starts = (await session.execute(
            select(func.count())
            .select_from(FunnelEvent)
            .where(FunnelEvent.event_type == "bot_started")
            .where(FunnelEvent.created_at >= day_start_utc)
        )).scalar() or 0

        # Today's new candidates by type
        new_by_type = (await session.execute(
            select(
                Candidate.candidate_type,
                func.count().label("cnt"),
            )
            .where(Candidate.created_at >= day_start_utc)
            .group_by(Candidate.candidate_type)
        )).all()

        # Today's screenings completed
        screenings = (await session.execute(
            select(
                Candidate.recommendation,
                func.count().label("cnt"),
            )
            .where(Candidate.recommendation.isnot(None))
            .where(Candidate.updated_at >= day_start_utc)
            .where(Candidate.status.in_(["screened", "pending_crm_approval", "interview_invited", "declined"]))
            .group_by(Candidate.recommendation)
        )).all()

        # Today's interview outcomes
        interview_outcomes = (await session.execute(
            select(
                Candidate.interview_confirmed,
                func.count().label("cnt"),
            )
            .where(Candidate.huntme_crm_slot.like(f"{today_str}%"))
            .group_by(Candidate.interview_confirmed)
        )).all()

        # All-time totals
        totals = (await session.execute(
            select(
                Candidate.candidate_type,
                func.count().label("cnt"),
            )
            .group_by(Candidate.candidate_type)
        )).all()

        # Show-up rate (all-time)
        confirmed_count = (await session.execute(
            select(func.count())
            .where(Candidate.interview_confirmed == "confirmed")
        )).scalar() or 0
        total_invited = (await session.execute(
            select(func.count())
            .where(Candidate.status == "interview_invited")
        )).scalar() or 0

    # Format
    lines = [f"\ud83c\udf19 DAILY REPORT \u2014 {date_display}\n"]

    # Activity
    new_total = sum(r.cnt for r in new_by_type)
    new_parts = [f"{r.cnt} {r.candidate_type}" for r in new_by_type if r.candidate_type]
    new_detail = f" ({', '.join(new_parts)})" if new_parts else ""

    lines.append("\ud83d\udcc8 TODAY'S ACTIVITY:")
    lines.append(f"  \ud83d\udc4b Bot starts: {bot_starts}")
    lines.append(f"  \ud83c\udd95 New candidates: {new_total}{new_detail}")

    screen_total = sum(r.cnt for r in screenings)
    if screen_total:
        s_map = {r.recommendation: r.cnt for r in screenings}
        lines.append(
            f"  \ud83d\udcdd Screenings: {screen_total} "
            f"(\u2705 {s_map.get('PASS', 0)} | \ud83d\udfe1 {s_map.get('MAYBE', 0)} | \u274c {s_map.get('REJECT', 0)})"
        )

    # By offer
    if new_by_type:
        lines.append("\n\ud83c\udfaf BY OFFER:")
        for r in new_by_type:
            if r.candidate_type:
                lines.append(f"  {r.candidate_type.capitalize()}s: +{r.cnt} new")

    # Interview outcomes
    i_map = {r.interview_confirmed: r.cnt for r in interview_outcomes}
    has_interviews = any(i_map.values())
    if has_interviews:
        lines.append("\n\ud83d\udcc5 INTERVIEWS:")
        if i_map.get("confirmed"):
            lines.append(f"  \u2705 Confirmed: {i_map['confirmed']}")
        if i_map.get("cancelled"):
            lines.append(f"  \ud83d\udeab Cancelled: {i_map['cancelled']}")
        no_resp = i_map.get(None, 0)
        if no_resp:
            lines.append(f"  \ud83d\udd34 No response: {no_resp}")

    # All-time totals
    grand_total = sum(r.cnt for r in totals)
    totals_parts = [f"{r.cnt} {r.candidate_type}s" for r in totals if r.candidate_type]
    show_rate = f"{confirmed_count * 100 // total_invited}%" if total_invited else "n/a"

    lines.append(f"\n\ud83d\udcca ALL-TIME TOTALS:")
    lines.append(f"  Total candidates: {grand_total}")
    if totals_parts:
        lines.append(f"  {' | '.join(totals_parts)}")
    lines.append(f"  Interview show-up rate: {show_rate}")

    return "\n".join(lines)


# ── background loop ──

_last_morning_date: str | None = None
_last_evening_date: str | None = None


async def run_daily_reports(bot: Bot):
    """Background loop: send morning + evening reports to admin chat."""
    global _last_morning_date, _last_evening_date

    # Small delay to let bot fully start
    await asyncio.sleep(5)
    logger.info("Daily reports checker started (morning=%d:00, evening=%d:00 +5)",
                _MORNING_HOUR, _EVENING_HOUR)

    while True:
        try:
            now = _now_yek()
            today = now.strftime("%Y-%m-%d")

            # Morning report
            if now.hour >= _MORNING_HOUR and _last_morning_date != today:
                _last_morning_date = today
                text = await _build_morning_report()
                await bot.send_message(config.ADMIN_CHAT_ID, text)
                logger.info("Morning report sent")

            # Evening report
            if now.hour >= _EVENING_HOUR and _last_evening_date != today:
                _last_evening_date = today
                text = await _build_evening_report()
                await bot.send_message(config.ADMIN_CHAT_ID, text)
                logger.info("Evening report sent")

        except Exception:
            logger.exception("Daily report error")

        await asyncio.sleep(_CHECK_INTERVAL)
