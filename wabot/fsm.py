"""Funnel FSM — 25-step WA conversation for BR model recruitment.

State stored in Neon DB (wa_leads.step + wa_leads.state JSON).
Triggers: "+" → next step, "1"/"2" → branching, free text → AI.

Includes:
- Model funnel (steps 0-16)
- Agent fallback branch (steps 100-104)
- Follow-up system (1h/24h/72h → cold)
- Retention messages (post-booking milestones)
"""
import json
import logging
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from wabot import bitrix, waha_client, ai
from wabot.models import WaLead
from wabot.messages.pt import (
    STEPS, FOLLOWUP, CAPYBARA_MEME_URL, GABI_PHOTO_URL,
    AGENT_DISQUALIFY_TEMPLATES, AGENT_STEPS,
    RETENTION_BOOKING_CONFIRMED, RETENTION_POST_INTERVIEW,
    RETENTION_DAILY_MOTIVATION, RETENTION_7_SHIFTS,
)

logger = logging.getLogger(__name__)

# Agent branch step range
AGENT_STEP_MIN = 100
AGENT_STEP_MAX = 104


async def get_or_create_lead(session: AsyncSession, phone: str, source: str = "wa_ad") -> WaLead:
    result = await session.execute(select(WaLead).where(WaLead.phone == phone))
    lead = result.scalar_one_or_none()
    if lead is None:
        lead = WaLead(phone=phone, source=source, step=0)
        session.add(lead)
        await session.flush()
        # Create in Bitrix24
        bitrix_id = await bitrix.create_lead(phone=phone, source=source)
        if bitrix_id:
            lead.bitrix_id = bitrix_id
        await session.commit()
        logger.info("New WA lead: %s", phone)
    return lead


def _get_state(lead: WaLead) -> dict:
    try:
        return json.loads(lead.state or "{}")
    except Exception:
        return {}


def _set_state(lead: WaLead, state: dict):
    lead.state = json.dumps(state, ensure_ascii=False)


def _is_agent_branch(lead: WaLead) -> bool:
    """Check if lead is in the agent fallback branch."""
    return AGENT_STEP_MIN <= lead.step <= AGENT_STEP_MAX or lead.role == "agent"


async def _send_step(phone: str, step: int, state: Optional[dict] = None):
    """Send all messages for a given step."""
    if step == 0:
        # Special: send capybara meme image first
        await waha_client.send_image(phone, CAPYBARA_MEME_URL)

    # Check agent steps first, then model steps
    messages = AGENT_STEPS.get(step) or STEPS.get(step)
    if messages:
        # Template substitution for agent steps that use {name}
        if state:
            name = state.get("name", "")
            if name:
                messages = [m.replace("{name}", name) for m in messages]
        await waha_client.send_messages(phone, messages)


async def _handle_branch(lead: WaLead, session: AsyncSession, choice: str) -> bool:
    """Handle numbered choices. Returns True if handled."""
    step = lead.step
    state = _get_state(lead)

    # Step 11: device choice (1=Android, 2=iPhone)
    if step == 11:
        state["device"] = "Android" if choice == "1" else "iPhone"
        lead.device = state["device"]
        _set_state(lead, state)
        if lead.bitrix_id:
            await bitrix.update_lead(lead.bitrix_id, fields={"UF_CRM_DEVICE": lead.device})
        lead.step = 12
        await session.commit()
        await _send_step(lead.phone, 12)
        return True

    # Step 13: availability (1=Yes, 2=Not sure)
    if step == 13:
        state["available"] = choice == "1"
        _set_state(lead, state)
        lead.step = 14
        await session.commit()
        await _send_step(lead.phone, 14)
        if lead.bitrix_id:
            await bitrix.update_lead(lead.bitrix_id, stage=bitrix.STAGE_QUALIFIED)
            await bitrix.set_step(lead.bitrix_id, 14)
        return True

    return False


async def process_message(session: AsyncSession, phone: str, text: str, source: str = "wa_ad"):
    """Main entry point — process incoming WA message."""
    text = text.strip()

    lead = await get_or_create_lead(session, phone, source)

    # Human mode: bot is silent, agent handles manually
    if lead.human_mode:
        return

    # Update last message timestamp, reset follow-up counter on ANY response
    lead.last_message_at = datetime.now(timezone.utc)
    lead.followup_count = 0

    # If lead was cold/paused and comes back, reactivate
    if lead.status in ("cold", "paused"):
        lead.status = "active"
        if lead.bitrix_id:
            await bitrix.update_lead(lead.bitrix_id, stage=bitrix.STAGE_ENGAGED)
            await bitrix.add_note(lead.bitrix_id, "Lead reactivated after silence")

    # --- AGENT BRANCH HANDLING ---
    if _is_agent_branch(lead):
        await _process_agent_message(lead, session, text)
        return

    # First ever message → start funnel from step 0
    if lead.step == 0 and text:
        await _send_step(phone, 0)
        lead.step = 1
        await session.commit()
        await _send_step(phone, 1)
        if lead.bitrix_id:
            await bitrix.update_lead(lead.bitrix_id, stage=bitrix.STAGE_ENGAGED)
            await bitrix.add_note(lead.bitrix_id, f"Primeiro contato WA. Texto: {text[:100]}")
        return

    # "+" → advance to next step
    if text == "+":
        next_step = lead.step + 1

        # Step 12: expect city text, not "+"
        if lead.step == 12:
            await waha_client.send_text(phone, "Me conta de qual cidade você é? 😊")
            return

        # Step 16: trigger interview booking
        if next_step == 16:
            await _trigger_booking(lead, session)
            return

        if next_step in STEPS:
            lead.step = next_step
            await session.commit()
            await _send_step(phone, next_step)
            if lead.bitrix_id:
                await bitrix.set_step(lead.bitrix_id, next_step)
        else:
            # End of defined steps — hand off
            await _trigger_booking(lead, session)
        return

    # Numbered choice (branching)
    if text in ("1", "2"):
        handled = await _handle_branch(lead, session, text)
        if handled:
            return

    # Step 12: collect city
    if lead.step == 12 and len(text) > 1:
        state = _get_state(lead)
        state["city"] = text
        lead.city = text
        _set_state(lead, state)
        lead.step = 13
        await session.commit()
        await _send_step(phone, 13)
        if lead.bitrix_id:
            await bitrix.update_lead(lead.bitrix_id, fields={"UF_CRM_CITY": text})
            await bitrix.set_step(lead.bitrix_id, 13)
        return

    # Free text → AI response
    state = _get_state(lead)
    context = f"Step {lead.step}. Collected data: {json.dumps(state, ensure_ascii=False)}"
    reply = await ai.get_response(text, context=context, step=lead.step)
    if reply:
        await waha_client.send_text(phone, reply)
        if lead.bitrix_id:
            await bitrix.add_note(lead.bitrix_id, f"[AI] User: {text[:100]}\nGabi: {reply[:100]}")
    else:
        # AI fallback
        await waha_client.send_text(phone, "Me conta mais! 😊 Ou manda *+* pra continuar.")

    await session.commit()


# =====================================================================
# AGENT FALLBACK BRANCH
# =====================================================================

async def offer_agent_role(lead: WaLead, session: AsyncSession, reason: str = "generic"):
    """Offer agent role to a disqualified model candidate.

    Args:
        lead: The WaLead being disqualified.
        session: DB session.
        reason: One of 'age', 'device', 'generic'.
    """
    state = _get_state(lead)
    name = state.get("name", lead.name or "")

    template = AGENT_DISQUALIFY_TEMPLATES.get(reason, AGENT_DISQUALIFY_TEMPLATES["generic"])
    msg = template.format(name=name or "Amiga")

    lead.disqualify_reason = reason
    # Don't change role yet — wait for their response
    # Mark step as special "waiting for agent decision"
    lead.step = 99  # temporary: waiting for yes/no to agent offer
    await session.commit()

    await waha_client.send_text(lead.phone, msg)

    if lead.bitrix_id:
        await bitrix.add_note(
            lead.bitrix_id,
            f"Model disqualified ({reason}). Agent role offered.",
        )


async def _process_agent_message(lead: WaLead, session: AsyncSession, text: str):
    """Process messages in the agent branch (steps 99-104)."""
    state = _get_state(lead)

    # Step 99: waiting for yes/no to agent offer
    if lead.step == 99:
        positive = _is_positive_response(text)
        if positive:
            lead.role = "agent"
            lead.status = "active"
            lead.step = 100
            await session.commit()
            await _send_step(lead.phone, 100, state)
            if lead.bitrix_id:
                await bitrix.add_note(lead.bitrix_id, "Accepted agent role offer")
        else:
            # Declined — graceful exit
            lead.status = "rejected"
            await session.commit()
            await waha_client.send_text(
                lead.phone,
                "Entendido! Se mudar de ideia, é só me chamar. "
                "Boa sorte com tudo! 💛",
            )
            if lead.bitrix_id:
                await bitrix.add_note(lead.bitrix_id, "Declined agent role offer")
                await bitrix.update_lead(lead.bitrix_id, stage=bitrix.STAGE_REJECTED)
        return

    # Step 100: agent intro — "+" to continue
    if lead.step == 100:
        if text == "+":
            lead.step = 101
            await session.commit()
            await _send_step(lead.phone, 101, state)
        else:
            await waha_client.send_text(lead.phone, "Manda *+* pra continuar 👇")
        return

    # Step 101: collect agent name
    if lead.step == 101:
        if len(text) > 1:
            state["name"] = text.strip().title()
            lead.name = state["name"]
            _set_state(lead, state)
            lead.step = 102
            await session.commit()
            await _send_step(lead.phone, 102, state)
            if lead.bitrix_id:
                await bitrix.update_lead(lead.bitrix_id, name=state["name"])
        else:
            await waha_client.send_text(lead.phone, "Me fala seu nome 😊")
        return

    # Step 102: collect contact method
    if lead.step == 102:
        if len(text) > 1:
            state["agent_contact"] = text.strip()
            _set_state(lead, state)
            lead.step = 103
            await session.commit()
            await _send_step(lead.phone, 103, state)
        else:
            await waha_client.send_text(
                lead.phone,
                "Qual a melhor forma de te contatar? (Instagram, Telegram, email...)",
            )
        return

    # Step 103: how they'll recruit
    if lead.step == 103:
        if len(text) > 1:
            state["agent_method"] = text.strip()
            _set_state(lead, state)
            lead.step = 104
            lead.status = "agent"
            await session.commit()
            await _send_step(lead.phone, 104, state)
            if lead.bitrix_id:
                await bitrix.update_lead(lead.bitrix_id, stage=bitrix.STAGE_APPROVED)
                await bitrix.add_note(
                    lead.bitrix_id,
                    f"Agent onboarded. Contact: {state.get('agent_contact', '?')}. "
                    f"Method: {state.get('agent_method', '?')}",
                )
            # Notify admin about new agent
            await _notify_admin_agent(lead, state)
        else:
            await waha_client.send_text(
                lead.phone,
                "Me conta como você pretende indicar meninas? 😊",
            )
        return

    # Step 104: agent is confirmed — any further message goes to AI
    context = f"Agent branch done. Agent data: {json.dumps(state, ensure_ascii=False)}"
    reply = await ai.get_response(text, context=context, step=lead.step)
    if reply:
        await waha_client.send_text(lead.phone, reply)
    else:
        await waha_client.send_text(
            lead.phone,
            "Qualquer dúvida sobre o programa de indicação, é só perguntar! 💛",
        )
    await session.commit()


def _is_positive_response(text: str) -> bool:
    """Check if text is a positive response (sim, quero, yes, +, etc.)."""
    text_lower = text.lower().strip()
    positive_words = {
        "sim", "s", "quero", "bora", "vamos", "pode", "claro", "yes",
        "si", "ok", "beleza", "show", "dale", "top", "vamo", "+",
        "1", "quero sim", "pode ser", "bora lá",
    }
    return text_lower in positive_words or any(w in text_lower for w in ["sim", "quero", "bora"])


# =====================================================================
# BOOKING & NOTIFICATIONS
# =====================================================================

async def _trigger_booking(lead: WaLead, session: AsyncSession):
    """Move lead to interview booking stage."""
    lead.status = "booked"
    lead.step = 16
    await session.commit()

    await waha_client.send_messages(lead.phone, STEPS[16])

    if lead.bitrix_id:
        await bitrix.update_lead(lead.bitrix_id, stage=bitrix.STAGE_INTERVIEW)
        await bitrix.add_note(lead.bitrix_id, "Lead moved to interview booking stage")

    # Notify TG admin
    await _notify_admin(lead)


async def _notify_admin(lead: WaLead):
    """Send TG notification to admin about qualified WA lead."""
    from wabot.config import config
    import aiohttp
    msg = (
        f"🇧🇷 *Novo lead qualificado WA*\n"
        f"📱 {lead.phone}\n"
        f"📍 {lead.city or '—'}\n"
        f"📲 {lead.device or '—'}\n"
        f"🔗 Bitrix ID: {lead.bitrix_id or '—'}"
    )
    if not config.BOT_TOKEN or not config.ADMIN_CHAT_ID:
        return
    try:
        async with aiohttp.ClientSession() as s:
            await s.post(
                f"https://api.telegram.org/bot{config.BOT_TOKEN}/sendMessage",
                json={"chat_id": config.ADMIN_CHAT_ID, "text": msg, "parse_mode": "Markdown"},
                timeout=aiohttp.ClientTimeout(total=5),
            )
    except Exception as e:
        logger.warning("Admin notify failed: %s", e)


async def _notify_admin_agent(lead: WaLead, state: dict):
    """Send TG notification about a new agent sign-up."""
    from wabot.config import config
    import aiohttp
    msg = (
        f"🤝 *Novo agente WA (fallback)*\n"
        f"📱 {lead.phone}\n"
        f"👤 {state.get('name', '—')}\n"
        f"📬 Contato: {state.get('agent_contact', '—')}\n"
        f"📋 Método: {state.get('agent_method', '—')}\n"
        f"🔗 Bitrix ID: {lead.bitrix_id or '—'}"
    )
    if not config.BOT_TOKEN or not config.ADMIN_CHAT_ID:
        return
    try:
        async with aiohttp.ClientSession() as s:
            await s.post(
                f"https://api.telegram.org/bot{config.BOT_TOKEN}/sendMessage",
                json={"chat_id": config.ADMIN_CHAT_ID, "text": msg, "parse_mode": "Markdown"},
                timeout=aiohttp.ClientTimeout(total=5),
            )
    except Exception as e:
        logger.warning("Admin agent notify failed: %s", e)


# =====================================================================
# FOLLOW-UP SYSTEM
# =====================================================================

async def send_followup(session: AsyncSession, phone: str):
    """Send scheduled follow-up message. Marks cold after 3rd."""
    result = await session.execute(select(WaLead).where(WaLead.phone == phone))
    lead = result.scalar_one_or_none()
    if not lead or lead.human_mode:
        return
    # Only send follow-ups to active leads (not booked, cold, rejected, agent)
    if lead.status not in ("active",):
        return

    lead.followup_count += 1
    count = lead.followup_count

    msg = FOLLOWUP.get(count)
    if msg:
        await waha_client.send_text(phone, msg)
        if lead.bitrix_id:
            await bitrix.add_note(lead.bitrix_id, f"Follow-up #{count} sent")

    # After 3rd follow-up (72h) with no response → mark as cold
    if count >= 3:
        lead.status = "cold"
        if lead.bitrix_id:
            await bitrix.update_lead(lead.bitrix_id, stage=bitrix.STAGE_PAUSED)
            await bitrix.add_note(lead.bitrix_id, "Lead marked as cold after 72h silence")

    await session.commit()


# =====================================================================
# RETENTION SYSTEM (post-booking milestones)
# =====================================================================

async def send_retention_message(session: AsyncSession, phone: str, milestone: str):
    """Send retention message based on milestone.

    Milestones:
        booking_confirmed — immediately after booking (Day 0)
        post_interview — Day 1 after interview
        work_day_N — Days 1-5 of working (N=1..5)
        shift_7 — After 7 completed shifts
    """
    result = await session.execute(select(WaLead).where(WaLead.phone == phone))
    lead = result.scalar_one_or_none()
    if not lead or lead.human_mode:
        return

    if milestone == "booking_confirmed":
        state = _get_state(lead)
        date_str = state.get("interview_date", lead.huntme_slot or "em breve")
        msg = RETENTION_BOOKING_CONFIRMED.format(date=date_str)
        await waha_client.send_text(phone, msg)
        lead.retention_day = 0
        if lead.bitrix_id:
            await bitrix.add_note(lead.bitrix_id, "Retention: booking confirmed msg sent")

    elif milestone == "post_interview":
        await waha_client.send_text(phone, RETENTION_POST_INTERVIEW)
        lead.retention_day = 1
        if lead.bitrix_id:
            await bitrix.add_note(lead.bitrix_id, "Retention: post-interview msg sent")

    elif milestone.startswith("work_day_"):
        try:
            day = int(milestone.split("_")[-1])
        except ValueError:
            logger.warning("Invalid work day milestone: %s", milestone)
            return
        if day < 1 or day > 5:
            return
        # Avoid sending duplicate
        if lead.retention_day >= day:
            return
        # Pick from rotating templates (0-indexed)
        template = RETENTION_DAILY_MOTIVATION[(day - 1) % len(RETENTION_DAILY_MOTIVATION)]
        msg = template.format(day=day)
        await waha_client.send_text(phone, msg)
        lead.retention_day = day
        lead.shifts_completed = day
        if lead.bitrix_id:
            await bitrix.add_note(lead.bitrix_id, f"Retention: work day {day} msg sent")

    elif milestone == "shift_7":
        if lead.retention_day >= 7:
            return
        await waha_client.send_text(phone, RETENTION_7_SHIFTS)
        lead.retention_day = 7
        lead.shifts_completed = 7
        if lead.bitrix_id:
            await bitrix.add_note(lead.bitrix_id, "Retention: 7 shifts milestone msg sent")

    else:
        logger.warning("Unknown retention milestone: %s", milestone)
        return

    await session.commit()
