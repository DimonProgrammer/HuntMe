"""Agent application flow — collects CRM-required fields + auto-submits.

Triggered from operator decline redirect or future menu role selection.
Steps: [name (if unknown)] → DOB → phone → CRM submit → welcome message
Telegram @username captured automatically from TG API.
"""

import asyncio
import logging
import re
from datetime import datetime

from aiogram import Bot, F, Router
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup, Message
from sqlalchemy import select

from bot.config import config
from bot.database import async_session
from bot.database.models import Candidate
from bot.messages import msg
from bot.services import huntme_crm

logger = logging.getLogger(__name__)
router = Router()


async def send_agent_offer(bot: Bot, chat_id: int, text: str, lang: str = "en") -> None:
    """Send agent offer text + video + become_agent button.

    Used from: admin reject, overage decline, AI decline.
    """
    m = msg(lang)
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=m.BTN_BECOME_AGENT, callback_data="become_agent")],
    ])
    full_text = text + m.AGENT_OFFER_BLOCK

    if config.AGENT_VIDEO_FILE_ID:
        try:
            await bot.send_video(chat_id, config.AGENT_VIDEO_FILE_ID)
        except Exception:
            logger.debug("Failed to send agent video to %s", chat_id)

    await bot.send_message(chat_id, full_text, reply_markup=kb)


async def send_agent_presentation(bot: Bot, chat_id: int, lang: str = "en") -> None:
    """Send 4-message agent presentation with 5s delays, then ask if ready."""
    m = msg(lang)
    await bot.send_message(chat_id, m.AGENT_MSG_1_INTRO)
    await asyncio.sleep(5)
    await bot.send_message(chat_id, m.AGENT_MSG_2_SUPPORT)
    await asyncio.sleep(5)
    await bot.send_message(chat_id, m.AGENT_MSG_3_EARNINGS)
    await asyncio.sleep(5)
    await bot.send_message(chat_id, m.AGENT_MSG_4_CTA)
    await asyncio.sleep(2)
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=m.BTN_AGENT_YES, callback_data="agent_yes")],
        [InlineKeyboardButton(text=m.BTN_AGENT_MAYBE, callback_data="agent_maybe")],
    ])
    await bot.send_message(chat_id, m.AGENT_READY_CHECK, reply_markup=kb)


class AgentForm(StatesGroup):
    waiting_name = State()
    waiting_ready_check = State()
    waiting_dob = State()
    waiting_phone = State()


# --- Step 1 (fallback): Name ---

@router.message(AgentForm.waiting_name)
async def agent_name(message: Message, state: FSMContext):
    name = (message.text or "").strip()
    data = await state.get_data()
    lang = data.get("language", "en")
    m = msg(lang)

    if len(name) < 2 or len(name) > 50:
        await message.answer(m.STEP_NAME_VALIDATION)
        return

    await state.update_data(name=name)
    first_name = name.split()[0] if name else name
    await message.answer(m.STEP_NAME_GREETING.format(name=first_name))
    await send_agent_presentation(message.bot, message.chat.id, lang)
    await state.set_state(AgentForm.waiting_ready_check)


# --- Ready Check: Yes/No ---

@router.callback_query(AgentForm.waiting_ready_check, F.data == "agent_yes")
async def agent_ready_yes(callback: CallbackQuery, state: FSMContext):
    """User confirmed interest in agent role."""
    await callback.answer()
    data = await state.get_data()
    lang = data.get("language", "en")
    m = msg(lang)

    await state.set_state(AgentForm.waiting_dob)
    await callback.message.answer(
        f"{m.AGENT_STEP_DOB_INTRO}\n\n{m.AGENT_STEP_DOB}"
    )


@router.callback_query(AgentForm.waiting_ready_check, F.data == "agent_maybe")
async def agent_ready_maybe(callback: CallbackQuery, state: FSMContext):
    """User declined for now — show share link."""
    await callback.answer()
    data = await state.get_data()
    lang = data.get("language", "en")
    m = msg(lang)

    share_url = (
        "https://t.me/share/url?url=https://apextalent.pro/ru"
        if lang == "ru"
        else "https://t.me/share/url?url=https://apextalent.pro"
    )
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=m.BTN_SHARE_REFERRAL, url=share_url)],
    ])

    await state.clear()
    await callback.message.answer(m.AGENT_DECLINED, reply_markup=kb)


# --- Step 2: Date of Birth ---

def _parse_dob(text: str):
    """Parse dd.mm.yyyy, return (date, error_key)."""
    text = text.strip().replace("/", ".").replace("-", ".")
    match = re.match(r"^(\d{1,2})\.(\d{1,2})\.(\d{4})$", text)
    if not match:
        return None, "format"
    try:
        day, month, year = int(match.group(1)), int(match.group(2)), int(match.group(3))
        dob = datetime(year, month, day)
    except (ValueError, OverflowError):
        return None, "format"
    if dob >= datetime.now():
        return None, "future"
    age = (datetime.now() - dob).days // 365
    if age < 18:
        return None, "underage"
    return dob, None


@router.message(AgentForm.waiting_dob)
async def agent_dob(message: Message, state: FSMContext):
    data = await state.get_data()
    lang = data.get("language", "en")
    m = msg(lang)

    dob, error = _parse_dob(message.text or "")
    if error == "underage":
        await message.answer(m.DECLINE_UNDERAGE)
        await state.clear()
        return
    if error:
        await message.answer(m.AGENT_STEP_DOB_VALIDATION)
        return

    await state.update_data(dob=dob.strftime("%d.%m.%Y"))
    await message.answer(m.AGENT_STEP_PHONE)
    await state.set_state(AgentForm.waiting_phone)


# --- Step 3: Phone ---

def _validate_phone(text: str) -> bool:
    """Basic phone validation: 7+ digits, allows +, spaces, dashes, parens."""
    digits = re.sub(r"[^\d]", "", text)
    return len(digits) >= 7


@router.message(AgentForm.waiting_phone)
async def agent_phone(message: Message, state: FSMContext):
    data = await state.get_data()
    lang = data.get("language", "en")
    m = msg(lang)

    phone = (message.text or "").strip()
    if not _validate_phone(phone):
        await message.answer(m.AGENT_STEP_PHONE_VALIDATION)
        return

    await state.update_data(phone=phone)
    data = await state.get_data()
    await state.clear()

    # Update or create candidate in DB
    tg_user_id = message.from_user.id
    try:
        async with async_session() as session:
            result = await session.execute(
                select(Candidate).where(Candidate.tg_user_id == tg_user_id)
            )
            cand = result.scalar_one_or_none()
            if cand:
                cand.status = "agent_applied"
                cand.candidate_type = "agent"
                cand.name = data.get("name", cand.name)
                cand.birth_date = data.get("dob")
                cand.phone_number = digits
                cand.phone_country = country
                cand.contact_info = phone
            else:
                cand = Candidate(
                    tg_user_id=tg_user_id,
                    tg_username=message.from_user.username,
                    name=data.get("name", "N/A"),
                    candidate_type="agent",
                    status="agent_applied",
                    language=data.get("language", "en"),
                    birth_date=data.get("dob"),
                    phone_number=digits,
                    phone_country=country,
                    contact_info=phone,
                )
                session.add(cand)
            await session.commit()
    except Exception:
        logger.exception("Failed to save agent candidate to DB")

    # Auto-submit to CRM
    digits, country = huntme_crm.parse_phone(phone)
    tg_handle = message.from_user.username or ""
    crm_ok, crm_error = await huntme_crm.submit_agent(
        name=data.get("name", "N/A"),
        birth_date=data.get("dob", ""),
        phone=digits,
        phone_country=country,
        telegram=tg_handle,
    )

    # Welcome message (always, even if CRM failed)
    try:
        await message.answer(m.AGENT_WELCOME, parse_mode="Markdown")
        msg_sent = True
    except Exception:
        logger.exception("Failed to send AGENT_WELCOME to candidate")
        msg_sent = False

    # Admin FYI notification (no approve/reject buttons)
    await _notify_admin_agent(
        message, data, digits=digits, country=country,
        crm_ok=crm_ok, crm_error=crm_error, msg_sent=msg_sent,
    )


# --- Admin notification ---

async def _notify_admin_agent(
    message: Message, data: dict,
    digits: str = "", country: str = "",
    crm_ok: bool = False, crm_error: str = None,
    msg_sent: bool = True,
):
    tg_username = message.from_user.username or ""
    tg_display = f"@{tg_username}" if tg_username else "no username"
    # Agent CRM uses full international number with + prefix
    full_number = f"+{digits}" if digits and not digits.startswith("+") else digits
    crm_status = "CRM submitted" if crm_ok else f"CRM failed: {crm_error or 'unknown'}"
    msg_status = "✅ sent" if msg_sent else "❌ FAILED to send"
    admin_text = (
        f"[AGENT {'✅' if crm_ok else '❌'} {crm_status}]\n\n"
        f"Name: {data.get('name', 'N/A')}\n"
        f"TG: {tg_display} (ID: {message.from_user.id})\n"
        f"DOB: {data.get('dob', 'N/A')}\n"
        f"Phone: {data.get('phone', 'N/A')}\n"
        f"Lang: {data.get('language', 'en').upper()}\n"
        f"Welcome msg: {msg_status}\n\n"
        f"CRM submitted data (JSON):\n"
        f"  Category: Team (1)\n"
        f"  Number: {full_number}\n"
        f"  Phone country: {country}\n"
        f"  Telegram: {tg_username}"
    )
    try:
        await message.bot.send_message(config.ADMIN_CHAT_ID, admin_text)
    except Exception:
        logger.exception("Failed to notify admin about agent application")
