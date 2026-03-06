"""Userbot outreach tasks.

Each task queries the Neon DB and sends personal messages to candidates
via the manager's Telegram account (not the bot).

Tasks:
  - interview_booked_followup  → message to candidates 1 day before interview
  - interview_noshow_followup  → message to candidates who missed their interview
  - agent_welcome              → warm welcome to new agents (first 2h after signup)
  - agent_reengagement         → nudge agents who haven't referred anyone in 3 days
"""

from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone

from sqlalchemy import select, update
from telethon import TelegramClient

from bot.database.connection import async_session
from bot.database.models import Candidate
from userbot import messages as tpl

logger = logging.getLogger(__name__)

# Manila timezone (CRM timezone)
from bot.services.huntme_crm import _MANILA_TZ


# ── Helpers ──────────────────────────────────────────────────────────────────

async def _send(client: TelegramClient, tg_user_id: int, text: str) -> bool:
    """Send a message; return True on success."""
    try:
        await client.send_message(tg_user_id, text, parse_mode="md")
        return True
    except Exception as exc:
        logger.warning("Failed to send to %s: %s", tg_user_id, exc)
        return False


def _pick(lang: str | None, en: str, ru: str) -> str:
    return ru if lang == "ru" else en


# ── Task 1: Interview booked follow-up ───────────────────────────────────────

async def interview_booked_followup(client: TelegramClient):
    """Send a personal pre-interview message the evening before the interview.

    Condition: interview_invited + slot tomorrow + personal_msg_sent is NULL.
    """
    now_manila = datetime.now(_MANILA_TZ)
    tomorrow = now_manila.date() + timedelta(days=1)

    async with async_session() as session:
        result = await session.execute(
            select(Candidate).where(
                Candidate.status == "interview_invited",
                Candidate.huntme_crm_submitted.is_(True),
                Candidate.huntme_crm_slot.isnot(None),
                Candidate.tg_user_id.isnot(None),
                Candidate.personal_msg_sent.is_(None),  # type: ignore[attr-defined]
            )
        )
        candidates = result.scalars().all()

    for cand in candidates:
        try:
            slot_dt = datetime.strptime(cand.huntme_crm_slot, "%d.%m.%Y %H:%M")
            slot_dt = slot_dt.replace(tzinfo=_MANILA_TZ)
        except Exception:
            continue

        if slot_dt.date() != tomorrow:
            continue

        time_str = slot_dt.strftime("%H:%M")
        text = _pick(
            cand.language,
            tpl.INTERVIEW_BOOKED_EN.format(name=cand.name or "there", time=time_str),
            tpl.INTERVIEW_BOOKED_RU.format(name=cand.name or "там", time=time_str),
        )
        if await _send(client, cand.tg_user_id, text):
            async with async_session() as session:
                await session.execute(
                    update(Candidate)
                    .where(Candidate.tg_user_id == cand.tg_user_id)
                    .values(personal_msg_sent=datetime.utcnow())
                )
                await session.commit()
            logger.info("Pre-interview message sent to %s (%s)", cand.name, cand.tg_user_id)


# ── Task 2: No-show follow-up ─────────────────────────────────────────────────

async def interview_noshow_followup(client: TelegramClient):
    """Send a follow-up to candidates whose slot passed but status is still interview_invited.

    Fires 3h after the slot time.
    """
    now_manila = datetime.now(_MANILA_TZ)

    async with async_session() as session:
        result = await session.execute(
            select(Candidate).where(
                Candidate.status == "interview_invited",
                Candidate.huntme_crm_slot.isnot(None),
                Candidate.tg_user_id.isnot(None),
                Candidate.noshow_msg_sent.is_(None),  # type: ignore[attr-defined]
            )
        )
        candidates = result.scalars().all()

    for cand in candidates:
        try:
            slot_dt = datetime.strptime(cand.huntme_crm_slot, "%d.%m.%Y %H:%M")
            slot_dt = slot_dt.replace(tzinfo=_MANILA_TZ)
        except Exception:
            continue

        # Only if slot was > 3h ago
        if (now_manila - slot_dt).total_seconds() < 3 * 3600:
            continue

        text = _pick(
            cand.language,
            tpl.INTERVIEW_NOSHOW_EN.format(name=cand.name or "there"),
            tpl.INTERVIEW_NOSHOW_RU.format(name=cand.name or ""),
        )
        if await _send(client, cand.tg_user_id, text):
            async with async_session() as session:
                await session.execute(
                    update(Candidate)
                    .where(Candidate.tg_user_id == cand.tg_user_id)
                    .values(noshow_msg_sent=datetime.utcnow())
                )
                await session.commit()
            logger.info("No-show message sent to %s (%s)", cand.name, cand.tg_user_id)


# ── Task 3: Agent welcome ─────────────────────────────────────────────────────

async def agent_welcome(client: TelegramClient):
    """Send a warm welcome to newly registered agents (within first 2h of signup)."""
    cutoff = datetime.utcnow() - timedelta(hours=2)

    async with async_session() as session:
        result = await session.execute(
            select(Candidate).where(
                Candidate.candidate_type == "agent",
                Candidate.status == "screened",
                Candidate.tg_user_id.isnot(None),
                Candidate.agent_welcome_sent.is_(None),  # type: ignore[attr-defined]
                Candidate.created_at >= cutoff,
            )
        )
        candidates = result.scalars().all()

    for cand in candidates:
        text = _pick(
            cand.language,
            tpl.AGENT_WELCOME_EN.format(name=cand.name or "there"),
            tpl.AGENT_WELCOME_RU.format(name=cand.name or ""),
        )
        if await _send(client, cand.tg_user_id, text):
            async with async_session() as session:
                await session.execute(
                    update(Candidate)
                    .where(Candidate.tg_user_id == cand.tg_user_id)
                    .values(agent_welcome_sent=datetime.utcnow())
                )
                await session.commit()
            logger.info("Agent welcome sent to %s (%s)", cand.name, cand.tg_user_id)


# ── Task 4: Agent re-engagement ───────────────────────────────────────────────

async def agent_reengagement(client: TelegramClient):
    """Nudge agents who have been active 3+ days but sent no referrals yet."""
    three_days_ago = datetime.utcnow() - timedelta(days=3)
    one_week_ago = datetime.utcnow() - timedelta(days=7)

    async with async_session() as session:
        result = await session.execute(
            select(Candidate).where(
                Candidate.candidate_type == "agent",
                Candidate.status == "screened",
                Candidate.tg_user_id.isnot(None),
                Candidate.agent_welcome_sent.isnot(None),  # type: ignore[attr-defined]
                Candidate.agent_reengagement_sent.is_(None),  # type: ignore[attr-defined]
                Candidate.created_at.between(one_week_ago, three_days_ago),
            )
        )
        candidates = result.scalars().all()

    for cand in candidates:
        text = _pick(
            cand.language,
            tpl.AGENT_REENGAGEMENT_EN.format(name=cand.name or "there"),
            tpl.AGENT_REENGAGEMENT_RU.format(name=cand.name or ""),
        )
        if await _send(client, cand.tg_user_id, text):
            async with async_session() as session:
                await session.execute(
                    update(Candidate)
                    .where(Candidate.tg_user_id == cand.tg_user_id)
                    .values(agent_reengagement_sent=datetime.utcnow())
                )
                await session.commit()
            logger.info("Agent re-engagement sent to %s (%s)", cand.name, cand.tg_user_id)
