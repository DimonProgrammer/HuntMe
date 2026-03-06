"""Funnel FSM — 25-step WA conversation for BR model recruitment.

State stored in Neon DB (wa_leads.step + wa_leads.state JSON).
Triggers: "+" → next step, "1"/"2" → branching, free text → AI.
"""
import json
import logging
from typing import Optional

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from wabot import bitrix, waha_client, ai
from wabot.models import WaLead
from wabot.messages.pt import STEPS, FOLLOWUP, CAPYBARA_MEME_URL, GABI_PHOTO_URL

logger = logging.getLogger(__name__)


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


async def _send_step(phone: str, step: int):
    """Send all messages for a given step."""
    if step == 0:
        # Special: send capybara meme image first
        await waha_client.send_image(phone, CAPYBARA_MEME_URL)

    messages = STEPS.get(step)
    if messages:
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

    # Update last message timestamp for follow-up scheduler
    from datetime import datetime, timezone
    lead.last_message_at = datetime.now(timezone.utc)
    lead.followup_count = 0

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


async def send_followup(session: AsyncSession, phone: str):
    """Send scheduled follow-up message."""
    result = await session.execute(select(WaLead).where(WaLead.phone == phone))
    lead = result.scalar_one_or_none()
    if not lead or lead.human_mode or lead.status not in ("active",):
        return

    lead.followup_count += 1
    count = lead.followup_count

    msg = FOLLOWUP.get(count)
    if msg:
        await waha_client.send_text(phone, msg)
        if lead.bitrix_id:
            await bitrix.add_note(lead.bitrix_id, f"Follow-up #{count} sent")

    if count >= 3:
        lead.status = "paused"
        if lead.bitrix_id:
            await bitrix.update_lead(lead.bitrix_id, stage=bitrix.STAGE_PAUSED)

    await session.commit()
