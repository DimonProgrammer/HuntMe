"""6-step FSM flow for Recruitment Agent qualification.

Triggered from operator decline redirect or future menu role selection.
Steps: name → region → english → experience → hours → contact
No AI screening — goes directly to admin for manual review.
"""

import logging

from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup, Message

from bot.config import config
from bot.messages import msg

logger = logging.getLogger(__name__)
router = Router()


class AgentForm(StatesGroup):
    waiting_name = State()
    waiting_region = State()
    waiting_english = State()
    waiting_experience = State()
    waiting_hours = State()
    waiting_contact = State()


# --- Step 1: Name ---

@router.message(AgentForm.waiting_name)
async def agent_name(message: Message, state: FSMContext):
    name = (message.text or "").strip()
    if len(name) < 2 or len(name) > 50:
        data = await state.get_data()
        lang = data.get("language", "en")
        m = msg(lang)
        await message.answer(m.STEP_NAME_VALIDATION)
        return
    await state.update_data(name=name)

    data = await state.get_data()
    lang = data.get("language", "en")
    m = msg(lang)

    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="Philippines", callback_data="aregion_ph"),
            InlineKeyboardButton(text="Nigeria", callback_data="aregion_ng"),
        ],
        [
            InlineKeyboardButton(text="Latin America", callback_data="aregion_latam"),
            InlineKeyboardButton(text="Other", callback_data="aregion_other"),
        ],
    ])
    first_name = name.split()[0] if name else name
    greeting = m.STEP_NAME_GREETING.format(name=first_name)
    await message.answer(
        f"{greeting}\n\n{m.AGENT_STEP_REGION}",
        reply_markup=keyboard,
    )
    await state.set_state(AgentForm.waiting_region)


# --- Step 2: Region ---

@router.callback_query(AgentForm.waiting_region, F.data.startswith("aregion_"))
async def agent_region(callback: CallbackQuery, state: FSMContext):
    region = callback.data.removeprefix("aregion_")
    await callback.answer()
    await state.update_data(region=region)

    data = await state.get_data()
    lang = data.get("language", "en")
    m = msg(lang)

    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="Beginner (A1-A2)", callback_data="aeng_beginner"),
            InlineKeyboardButton(text="Intermediate (B1)", callback_data="aeng_b1"),
        ],
        [
            InlineKeyboardButton(text="Upper-Intermediate (B2)", callback_data="aeng_b2"),
            InlineKeyboardButton(text="Advanced (C1+)", callback_data="aeng_c1"),
        ],
        [InlineKeyboardButton(text="Native / Fluent", callback_data="aeng_native")],
    ])
    await callback.message.answer(m.AGENT_STEP_ENGLISH, reply_markup=keyboard)
    await state.set_state(AgentForm.waiting_english)


# --- Step 3: English Level ---

@router.callback_query(AgentForm.waiting_english, F.data.startswith("aeng_"))
async def agent_english(callback: CallbackQuery, state: FSMContext):
    level = callback.data.removeprefix("aeng_")
    await callback.answer()

    data = await state.get_data()
    lang = data.get("language", "en")
    m = msg(lang)

    if level == "beginner":
        await state.update_data(english_level="beginner")
        await callback.message.answer(m.DECLINE_ENGLISH)
        await state.clear()
        return

    level_map = {"b1": "B1", "b2": "B2", "c1": "C1", "native": "Native"}
    await state.update_data(english_level=level_map.get(level, level))

    await callback.message.answer(m.AGENT_STEP_EXPERIENCE)
    await state.set_state(AgentForm.waiting_experience)


# --- Step 4: Recruiting Experience ---

@router.message(AgentForm.waiting_experience)
async def agent_experience(message: Message, state: FSMContext):
    await state.update_data(recruiting_experience=message.text.strip())

    data = await state.get_data()
    lang = data.get("language", "en")
    m = msg(lang)

    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="5-10 hrs/week", callback_data="ahours_5-10")],
        [InlineKeyboardButton(text="10-20 hrs/week", callback_data="ahours_10-20")],
        [InlineKeyboardButton(text="20+ hrs/week (full-time)", callback_data="ahours_20+")],
    ])
    await message.answer(m.AGENT_STEP_HOURS, reply_markup=keyboard)
    await state.set_state(AgentForm.waiting_hours)


# --- Step 5: Available Hours ---

@router.callback_query(AgentForm.waiting_hours, F.data.startswith("ahours_"))
async def agent_hours(callback: CallbackQuery, state: FSMContext):
    hours = callback.data.removeprefix("ahours_")
    await callback.answer()
    await state.update_data(available_hours=hours)

    data = await state.get_data()
    lang = data.get("language", "en")
    m = msg(lang)

    await callback.message.answer(m.AGENT_STEP_CONTACT)
    await state.set_state(AgentForm.waiting_contact)


# --- Step 6: Contact → Notify Admin ---

@router.message(AgentForm.waiting_contact)
async def agent_contact(message: Message, state: FSMContext):
    await state.update_data(contact_info=message.text.strip())
    data = await state.get_data()
    lang = data.get("language", "en")
    m = msg(lang)
    await state.clear()

    await message.answer(m.APPLICATION_RECEIVED)
    await _notify_admin_agent(message, data)


# --- Catch-all: text sent in button-only states ---

@router.message(AgentForm.waiting_region)
@router.message(AgentForm.waiting_english)
@router.message(AgentForm.waiting_hours)
async def agent_button_state_text(message: Message, state: FSMContext):
    """User typed text instead of pressing a button."""
    data = await state.get_data()
    lang = data.get("language", "en")
    m = msg(lang)
    await message.answer(m.USE_BUTTONS)


async def _notify_admin_agent(message: Message, data: dict):
    region_map = {"ph": "Philippines", "ng": "Nigeria", "latam": "Latin America", "other": "Other"}
    region_label = region_map.get(data.get("region", "other"), data.get("region", "N/A"))

    admin_text = (
        "[AGENT APPLICATION]\n\n"
        f"Name: {data.get('name', 'N/A')}\n"
        f"TG: @{message.from_user.username or 'N/A'} (ID: {message.from_user.id})\n"
        f"Region: {region_label}\n"
        f"English: {data.get('english_level', 'N/A')}\n"
        f"Recruiting Experience: {data.get('recruiting_experience', 'N/A')}\n"
        f"Available Hours: {data.get('available_hours', 'N/A')}/week\n"
        f"Contact: {data.get('contact_info', 'N/A')}"
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
