"""Inactivity reminder system for candidates in the screening flow.

Background task checks every 60s for candidates stuck in OperatorForm states.
Two reminder prompts max:
  1st at 10 min inactivity → "pick a time" with buttons
  2nd at 6h after 1st (if ignored) → different text, same buttons
If user picks a time → follow-up fires at that time, then stops.

Also runs interview day reminders:
- Morning at 09:00 Manila → confirmation prompt with Yes/No buttons
- 1h before slot → reminder to stay online
"""

from __future__ import annotations

import json
import logging
from datetime import datetime, timedelta, timezone

from aiogram import Bot
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from sqlalchemy import select, update

from bot.database.connection import async_session
from bot.config import config
from bot.database.models import Candidate, FsmState
from bot.messages import msg
from bot.services import huntme_crm
from bot.services.huntme_crm import _MANILA_TZ

logger = logging.getLogger(__name__)

# FSM state prefixes we monitor for inactivity
_MONITORED_PREFIXES = ("OperatorForm:", "InterviewBooking:", "ModelForm:")
# States where we should NOT send inactivity reminders
# (candidate is waiting for admin action or flow is complete)
_SKIP_STATES = frozenset({
    "InterviewBooking:waiting_crm_approval",
    "InterviewBooking:waiting_slot_notify",   # candidate waiting for slots to open
})
_MAX_PROMPTS = 2
_INACTIVITY_MINUTES = 10
_SECOND_PROMPT_HOURS = 6


def _reminder_kb(lang: str = "en") -> InlineKeyboardMarkup:
    m = msg(lang)
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="⏰ 30m", callback_data="remind_30"),
            InlineKeyboardButton(text="⏰ 1h", callback_data="remind_60"),
            InlineKeyboardButton(text="⏰ 3h", callback_data="remind_180"),
            InlineKeyboardButton(text="⏰ 12h", callback_data="remind_720"),
        ],
        [
            InlineKeyboardButton(text=m.BTN_CONTINUE, callback_data="remind_continue"),
        ],
    ])


# Keep legacy reference for any imports
REMINDER_KB = _reminder_kb("en")


async def run_reminder_checker(bot: Bot):
    """Background loop: every 60s check for inactive candidates."""
    import asyncio
    while True:
        await asyncio.sleep(60)
        try:
            await _process_reminders(bot)
        except Exception:
            logger.exception("Reminder check failed")


async def _process_reminders(bot: Bot):
    """Check all active FSM states for inactivity."""
    now = datetime.utcnow()
    threshold = now - timedelta(minutes=_INACTIVITY_MINUTES)

    async with async_session() as session:
        result = await session.execute(
            select(FsmState)
            .where(FsmState.state.isnot(None))
            .where(FsmState.updated_at < threshold)
        )
        rows = result.scalars().all()

    for fsm in rows:
        if not fsm.state:
            continue
        # Only monitor screening / booking states
        if not any(fsm.state.startswith(p) for p in _MONITORED_PREFIXES):
            continue
        # Skip states where candidate is waiting for admin (not actionable by candidate)
        if fsm.state in _SKIP_STATES:
            continue

        data = json.loads(fsm.data or "{}")

        # Hardware reminder: candidate postponed hardware question during booking
        hw_remind_at = data.get("hw_remind_at")
        if hw_remind_at and fsm.state == "InterviewBooking:waiting_hw_remind":
            try:
                remind_dt = datetime.fromisoformat(hw_remind_at)
                if remind_dt <= now:
                    await _send_hw_reminder(bot, fsm, data)
                    continue  # skip general inactivity logic for this candidate
            except Exception:
                logger.debug("Failed to parse hw_remind_at for %s", fsm.chat_id)

        prompt_count = data.get("reminder_count", 0)
        prompt_sent = data.get("reminder_prompt_sent_at")
        scheduled = data.get("reminder_scheduled_at")

        # User chose a time — check if it's due (works regardless of count)
        if scheduled:
            remind_at = datetime.fromisoformat(scheduled)
            if remind_at <= now:
                await _send_follow_up(bot, fsm, data)
            continue

        if prompt_count >= _MAX_PROMPTS:
            continue  # both prompts exhausted, stop

        if not prompt_sent:
            # No prompt yet → send 1st prompt
            await _send_reminder_prompt(bot, fsm, data)
        else:
            # Prompt sent but ignored → send 2nd prompt after 6h
            prompt_time = datetime.fromisoformat(prompt_sent)
            if prompt_time + timedelta(hours=_SECOND_PROMPT_HOURS) <= now:
                await _send_reminder_prompt(bot, fsm, data)


async def _send_reminder_prompt(bot: Bot, fsm: FsmState, data: dict):
    """Send 'choose reminder time' prompt (1st or 2nd based on count)."""
    chat_id = fsm.chat_id
    now = datetime.utcnow()
    lang = data.get("language", "en")
    m = msg(lang)
    count = data.get("reminder_count", 0)

    # Determine progress for personalized message
    step = (fsm.state or "").split(":")[-1]
    late_steps = {"waiting_internet", "waiting_start_date", "waiting_contact",
                  "waiting_birth_date", "waiting_phone", "waiting_experience",
                  "waiting_slot_choice"}
    is_late = step in late_steps

    if count == 0:
        text = m.REMINDER_FIRST_LATE if is_late else m.REMINDER_FIRST_EARLY
    else:
        text = m.REMINDER_SECOND_LATE if is_late else m.REMINDER_SECOND_EARLY

    try:
        await bot.send_message(chat_id, text, reply_markup=_reminder_kb(lang))
    except Exception:
        logger.debug("Failed to send reminder prompt to %s", chat_id)
        return

    data["reminder_prompt_sent_at"] = now.isoformat()
    data["reminder_count"] = count + 1
    await _update_fsm_data(fsm, data)


async def _send_follow_up(bot: Bot, fsm: FsmState, data: dict):
    """Send follow-up when user's scheduled reminder time arrives, then stop."""
    chat_id = fsm.chat_id
    lang = data.get("language", "en")
    m = msg(lang)

    try:
        await bot.send_message(chat_id, m.REMINDER_FOLLOWUP)
    except Exception:
        logger.debug("Failed to send follow-up to %s", chat_id)
        return

    # Done — set count to max so no more prompts fire
    data["reminder_count"] = _MAX_PROMPTS
    data["reminder_scheduled_at"] = None
    data["reminder_prompt_sent_at"] = None
    await _update_fsm_data(fsm, data)


async def _send_hw_reminder(bot: Bot, fsm: FsmState, data: dict):
    """Send hardware reminder and re-ask the pending hardware question."""
    from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
    chat_id = fsm.chat_id
    lang = data.get("language", "en")
    m = msg(lang)
    step = data.get("hw_remind_step", "cpu")

    step_texts = {
        "cpu": m.BOOKING_HW_CPU,
        "gpu": m.BOOKING_HW_GPU,
        "internet": m.BOOKING_HW_INTERNET,
    }
    hw_text = step_texts.get(step, m.BOOKING_HW_CPU)
    cant_now_kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=m.BTN_HW_CANT_NOW, callback_data="hw_cant_now")],
    ])

    # Update FSM state back to the appropriate waiting_hw_* state
    new_state_map = {
        "cpu": "InterviewBooking:waiting_hw_cpu",
        "gpu": "InterviewBooking:waiting_hw_gpu",
        "internet": "InterviewBooking:waiting_hw_internet",
    }
    new_state = new_state_map.get(step, "InterviewBooking:waiting_hw_cpu")

    try:
        await bot.send_message(chat_id, hw_text, reply_markup=cant_now_kb)
    except Exception:
        logger.debug("Failed to send hw reminder to %s", chat_id)
        return

    # Update FSM: restore hw_* waiting state and clear hw_remind_at
    data.pop("hw_remind_at", None)
    async with async_session() as session:
        row = await session.get(FsmState, (fsm.chat_id, fsm.user_id, fsm.bot_id))
        if row:
            row.state = new_state
            row.data = __import__("json").dumps(data, ensure_ascii=False)
            await session.commit()


async def _update_fsm_data(fsm: FsmState, data: dict):
    """Persist updated data dict back to fsm_states table."""
    async with async_session() as session:
        row = await session.get(FsmState, (fsm.chat_id, fsm.user_id, fsm.bot_id))
        if row:
            row.data = json.dumps(data, ensure_ascii=False)
            await session.commit()


# ═══ INTERVIEW DAY REMINDERS ═══


async def run_interview_reminder_checker(bot: Bot):
    """Background loop: every 60s check for upcoming interviews."""
    import asyncio
    while True:
        await asyncio.sleep(60)
        try:
            await _process_interview_reminders(bot)
        except Exception:
            logger.exception("Interview reminder check failed")


async def _process_interview_reminders(bot: Bot):
    """Send morning confirmation and 1h-before reminders for upcoming interviews."""
    now_manila = datetime.now(_MANILA_TZ)

    async with async_session() as session:
        result = await session.execute(
            select(Candidate)
            .where(Candidate.status == "interview_invited")
            .where(Candidate.huntme_crm_submitted.is_(True))
            .where(Candidate.huntme_crm_slot.isnot(None))
            .where(Candidate.tg_user_id.isnot(None))
        )
        candidates = result.scalars().all()

    for cand in candidates:
        try:
            slot_dt = datetime.strptime(cand.huntme_crm_slot, "%d.%m.%Y %H:%M")
            slot_dt = slot_dt.replace(tzinfo=_MANILA_TZ)
        except Exception:
            continue

        # Skip if slot already passed
        if slot_dt <= now_manila:
            continue

        m = msg(cand.language or "en")
        time_str = slot_dt.strftime("%H:%M")

        # Morning reminder: 09:00 Manila on interview day, slot still > 1h away
        morning_time = slot_dt.replace(hour=9, minute=0, second=0, microsecond=0)
        if (
            not cand.interview_morning_sent
            and slot_dt.date() == now_manila.date()
            and now_manila >= morning_time
            and (slot_dt - now_manila).total_seconds() > 3600
        ):
            await _send_interview_morning(bot, cand, m, time_str)

        # Retry reminder: 2h after morning send, if no response yet
        retry_time = morning_time + timedelta(hours=2)
        if (
            cand.interview_morning_sent
            and not cand.interview_retry_sent
            and not cand.interview_confirmed
            and now_manila >= retry_time
            and (slot_dt - now_manila).total_seconds() > 3600
        ):
            await _send_interview_retry(bot, cand, m, time_str)

        # 1-hour reminder
        one_hour_before = slot_dt - timedelta(hours=1)
        if (
            not cand.interview_reminder_sent
            and now_manila >= one_hour_before
        ):
            await _send_interview_1h(bot, cand, m, time_str)
            # Admin alert if not confirmed at 1h mark
            if cand.interview_confirmed != "confirmed":
                await _send_admin_no_response_alert(bot, cand, m)


async def _send_interview_morning(bot: Bot, cand: Candidate, m, time_str: str):
    """Send morning confirmation prompt with Yes/No buttons."""
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text=m.BTN_INTERVIEW_YES, callback_data="interview_confirm"),
            InlineKeyboardButton(text=m.BTN_INTERVIEW_NO, callback_data="interview_cancel"),
        ]
    ])
    try:
        await bot.send_message(
            cand.tg_user_id,
            m.INTERVIEW_MORNING_CONFIRM.format(name=cand.name or "there", time=time_str),
            reply_markup=kb,
        )
        # Mark as sent
        async with async_session() as session:
            await session.execute(
                update(Candidate)
                .where(Candidate.tg_user_id == cand.tg_user_id)
                .values(interview_morning_sent=True)
            )
            await session.commit()
        logger.info("Interview morning reminder sent to %s", cand.tg_user_id)
    except Exception:
        logger.debug("Failed to send interview morning reminder to %s", cand.tg_user_id)


async def _send_interview_1h(bot: Bot, cand: Candidate, m, time_str: str):
    """Send 1-hour-before reminder."""
    try:
        await bot.send_message(
            cand.tg_user_id,
            m.INTERVIEW_1H_REMINDER.format(time=time_str),
        )
        # Mark as sent
        async with async_session() as session:
            await session.execute(
                update(Candidate)
                .where(Candidate.tg_user_id == cand.tg_user_id)
                .values(interview_reminder_sent=True)
            )
            await session.commit()
        logger.info("Interview 1h reminder sent to %s", cand.tg_user_id)
    except Exception:
        logger.debug("Failed to send interview 1h reminder to %s", cand.tg_user_id)


async def _send_interview_retry(bot: Bot, cand: Candidate, m, time_str: str):
    """Send retry confirmation prompt if candidate didn't respond to morning reminder."""
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text=m.BTN_INTERVIEW_YES, callback_data="interview_confirm"),
            InlineKeyboardButton(text=m.BTN_INTERVIEW_NO, callback_data="interview_cancel"),
        ]
    ])
    try:
        await bot.send_message(
            cand.tg_user_id,
            m.INTERVIEW_RETRY_CONFIRM.format(name=cand.name or "there", time=time_str),
            reply_markup=kb,
        )
        async with async_session() as session:
            await session.execute(
                update(Candidate)
                .where(Candidate.tg_user_id == cand.tg_user_id)
                .values(interview_retry_sent=True)
            )
            await session.commit()
        logger.info("Interview retry reminder sent to %s", cand.tg_user_id)
    except Exception:
        logger.debug("Failed to send interview retry reminder to %s", cand.tg_user_id)


async def _send_admin_no_response_alert(bot: Bot, cand: Candidate, m):
    """Alert admin about unconfirmed candidate 1h before interview. Auto-set CRM to not confirmed."""
    slot = cand.huntme_crm_slot or "?"
    tg = cand.tg_username or str(cand.tg_user_id)
    status_label = cand.interview_confirmed or "no response"
    try:
        text = m.ADMIN_INTERVIEW_NO_RESPONSE.format(
            name=cand.name or "?", tg=tg, slot=slot,
        )
        if status_label == "cancelled":
            text = m.ADMIN_INTERVIEW_CANCELLED.format(
                name=cand.name or "?", tg=tg, slot=slot,
            )
        await bot.send_message(config.ADMIN_CHAT_ID, text)
    except Exception:
        logger.debug("Failed to send admin no-response alert for %s", cand.tg_user_id)
    # Auto-set CRM to "not confirmed" if app_id exists and not already cancelled
    if cand.huntme_crm_app_id and cand.interview_confirmed != "cancelled":
        ok, err = await huntme_crm.update_application_status(
            cand.huntme_crm_app_id, huntme_crm.CRM_STATUS_NOT_CONFIRMED
        )
        if not ok:
            logger.warning("CRM auto not-confirmed failed for app %s: %s", cand.huntme_crm_app_id, err)


# ═══ SLOT WAITING QUEUE ═══

_SLOT_CHECK_INTERVAL_SEC = 6 * 3600   # check every 6 hours
_SLOT_WAIT_MAX_DAYS = 4               # after 4 days without slots — send to support


async def run_slot_notify_checker(bot: Bot):
    """Every 6h: notify waiting candidates if slots opened in 4-day window."""
    import asyncio
    while True:
        await asyncio.sleep(_SLOT_CHECK_INTERVAL_SEC)
        try:
            await _process_slot_notifications(bot)
        except Exception:
            logger.exception("Slot notify checker error")


async def _process_slot_notifications(bot: Bot):
    """Check all slot-waiting candidates; notify if slots in 4-day window appeared."""
    from bot.handlers.interview_booking import _format_slot_display

    try:
        async with async_session() as session:
            result = await session.execute(
                select(Candidate).where(
                    Candidate.waiting_for_slot == True,  # noqa: E712
                    Candidate.tg_user_id.isnot(None),
                )
            )
            candidates = result.scalars().all()
    except Exception:
        logger.exception("Failed to query slot-waiting candidates")
        return

    if not candidates:
        return

    # One CRM request for all candidates
    raw_slots = await huntme_crm.get_available_slots(office_id=95)
    if raw_slots is None:
        return  # CRM unavailable — try again in 6h

    window_slots = huntme_crm.filter_slots_by_window(raw_slots, days=4)
    nearest = huntme_crm.pick_nearest_slots(window_slots, count=5) if window_slots else []

    expiry_cutoff = datetime.utcnow() - timedelta(days=_SLOT_WAIT_MAX_DAYS)

    for cand in candidates:
        tg_user_id = cand.tg_user_id
        lang = cand.language or "en"
        m_lang = msg(lang)

        # Check expiry: slot_wait_since > 4 days → send to support
        wait_since = cand.slot_wait_since or cand.updated_at
        if wait_since and wait_since < expiry_cutoff:
            try:
                await bot.send_message(tg_user_id, m_lang.BOOKING_SLOT_WAIT_EXPIRED)
                async with async_session() as session:
                    await session.execute(
                        update(Candidate)
                        .where(Candidate.tg_user_id == tg_user_id)
                        .values(waiting_for_slot=False, slot_wait_since=None)
                    )
                    await session.commit()
            except Exception:
                logger.debug("Failed to expire slot-wait for %s", tg_user_id)
            continue

        if not nearest:
            continue  # No slots yet — try again in 6h

        # Slots available — notify candidate
        try:
            buttons = [
                [InlineKeyboardButton(
                    text=_format_slot_display(slot_str),
                    callback_data=f"book_{slot_str.replace('.', '-').replace(' ', '_')}"
                )]
                for slot_str in nearest
            ]
            keyboard = InlineKeyboardMarkup(inline_keyboard=buttons)
            await bot.send_message(tg_user_id, m_lang.BOOKING_SLOTS_REOPENED, reply_markup=keyboard)

            # Update FSM state → waiting_slot_choice (FSM data preserved)
            async with async_session() as session:
                await session.execute(
                    update(FsmState)
                    .where(FsmState.chat_id == tg_user_id)
                    .where(FsmState.user_id == tg_user_id)
                    .where(FsmState.bot_id == bot.id)
                    .values(state="InterviewBooking:waiting_slot_choice")
                )
                await session.execute(
                    update(Candidate)
                    .where(Candidate.tg_user_id == tg_user_id)
                    .values(waiting_for_slot=False, slot_wait_since=None)
                )
                await session.commit()
        except Exception:
            logger.debug("Failed to notify slot-waiting candidate %s", tg_user_id)
