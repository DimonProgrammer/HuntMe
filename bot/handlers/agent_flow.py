"""Agent application flow — collects CRM-required fields.

Triggered from operator decline redirect or future menu role selection.
Steps: [name (if unknown)] → DOB → phone → admin notification
Telegram @username captured automatically from TG API.
"""

import asyncio
import logging
import re
from datetime import datetime

from aiogram import Bot, Router
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup, Message

from bot.config import config
from bot.messages import msg

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
    """Send 4-message agent presentation with 5s delays, ending with DOB question."""
    m = msg(lang)
    await bot.send_message(chat_id, m.AGENT_MSG_1_INTRO)
    await asyncio.sleep(5)
    await bot.send_message(chat_id, m.AGENT_MSG_2_SUPPORT)
    await asyncio.sleep(5)
    await bot.send_message(chat_id, m.AGENT_MSG_3_EARNINGS)
    await asyncio.sleep(5)
    await bot.send_message(chat_id, m.AGENT_MSG_4_CTA)


class AgentForm(StatesGroup):
    waiting_name = State()
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
    await state.set_state(AgentForm.waiting_dob)


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

    await message.answer(m.APPLICATION_RECEIVED)
    await _notify_admin_agent(message, data)


# --- Admin notification ---

async def _notify_admin_agent(message: Message, data: dict):
    tg_username = message.from_user.username or "N/A"
    admin_text = (
        "[AGENT APPLICATION]\n\n"
        f"Name: {data.get('name', 'N/A')}\n"
        f"TG: @{tg_username} (ID: {message.from_user.id})\n"
        f"DOB: {data.get('dob', 'N/A')}\n"
        f"Phone: {data.get('phone', 'N/A')}\n"
        f"Lang: {data.get('language', 'en').upper()}"
    )
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="✅ Approve Agent", callback_data=f"agentok_{message.from_user.id}"),
            InlineKeyboardButton(text="❌ Reject", callback_data=f"agentno_{message.from_user.id}"),
        ],
    ])
    try:
        await message.bot.send_message(config.ADMIN_CHAT_ID, admin_text, reply_markup=keyboard)
    except Exception:
        logger.exception("Failed to notify admin about agent application")
