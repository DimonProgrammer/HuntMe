"""Inactivity reminder system for candidates in the screening flow.

Background task checks every 60s for candidates stuck in OperatorForm states.
After 10 min inactivity → sends "choose reminder time" prompt.
If no response → auto-reminds at 1h, then 3h, then stops (max 3 reminders).
"""

from __future__ import annotations

import json
import logging
from datetime import datetime, timedelta

from aiogram import Bot
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from sqlalchemy import select

from bot.database.connection import async_session
from bot.database.models import FsmState

logger = logging.getLogger(__name__)

# FSM state prefixes we monitor for inactivity
_MONITORED_PREFIXES = ("OperatorForm:", "InterviewBooking:")
_MAX_REMINDERS = 3
_INACTIVITY_MINUTES = 10

# Reminder keyboard: 4 options in one row + Continue
REMINDER_KB = InlineKeyboardMarkup(inline_keyboard=[
    [
        InlineKeyboardButton(text="⏰ 30m", callback_data="remind_30"),
        InlineKeyboardButton(text="⏰ 1h", callback_data="remind_60"),
        InlineKeyboardButton(text="⏰ 3h", callback_data="remind_180"),
        InlineKeyboardButton(text="⏰ 12h", callback_data="remind_720"),
    ],
    [
        InlineKeyboardButton(text="▶️ Continue filling", callback_data="remind_continue"),
    ],
])


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

        data = json.loads(fsm.data or "{}")
        reminder_count = data.get("reminder_count", 0)
        if reminder_count >= _MAX_REMINDERS:
            continue

        prompt_sent = data.get("reminder_prompt_sent_at")
        scheduled = data.get("reminder_scheduled_at")

        if not prompt_sent:
            # First contact: send "choose time" prompt
            await _send_reminder_prompt(bot, fsm, data)
        elif scheduled:
            # User chose a time — check if it's due
            remind_at = datetime.fromisoformat(scheduled)
            if remind_at <= now:
                await _send_follow_up(bot, fsm, data)
        else:
            # User didn't respond to prompt — auto-remind after 1h
            prompt_time = datetime.fromisoformat(prompt_sent)
            if prompt_time + timedelta(hours=1) <= now:
                await _send_follow_up(bot, fsm, data)


async def _send_reminder_prompt(bot: Bot, fsm: FsmState, data: dict):
    """Send 'choose reminder time' message to candidate."""
    chat_id = fsm.chat_id
    now = datetime.utcnow()

    # Determine progress for personalized message
    step = (fsm.state or "").split(":")[-1]
    late_steps = {"waiting_internet", "waiting_start_date", "waiting_contact",
                  "waiting_birth_date", "waiting_phone", "waiting_experience",
                  "waiting_slot_choice"}
    if step in late_steps:
        text = (
            "Hey! You're almost done — just a couple more steps! 🏁\n\n"
            "If now's not a good time, pick when you'd like a reminder:"
        )
    else:
        text = (
            "Hey! 👋 No rush — if now's not a good time, "
            "pick when you'd like a reminder:"
        )

    try:
        await bot.send_message(chat_id, text, reply_markup=REMINDER_KB)
    except Exception:
        logger.debug("Failed to send reminder prompt to %s", chat_id)
        return

    # Update FSM data
    data["reminder_prompt_sent_at"] = now.isoformat()
    await _update_fsm_data(fsm, data)


async def _send_follow_up(bot: Bot, fsm: FsmState, data: dict):
    """Send a follow-up reminder and re-prompt the current step."""
    chat_id = fsm.chat_id
    count = data.get("reminder_count", 0) + 1

    from bot.services.followup import FOLLOWUP_TEMPLATES
    template = FOLLOWUP_TEMPLATES.get("silent_after_questions", {})
    text = template.get("message", "Hey! Just checking in — ready to continue? 🙂")

    try:
        await bot.send_message(chat_id, text)
    except Exception:
        logger.debug("Failed to send follow-up to %s", chat_id)
        return

    # Update: increment count, clear scheduled
    data["reminder_count"] = count
    data["reminder_scheduled_at"] = None
    data["reminder_prompt_sent_at"] = None  # allow re-prompt after next inactivity
    await _update_fsm_data(fsm, data)


async def _update_fsm_data(fsm: FsmState, data: dict):
    """Persist updated data dict back to fsm_states table."""
    async with async_session() as session:
        row = await session.get(FsmState, (fsm.chat_id, fsm.user_id, fsm.bot_id))
        if row:
            row.data = json.dumps(data, ensure_ascii=False)
            await session.commit()
