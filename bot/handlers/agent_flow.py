"""6-step FSM flow for Recruitment Agent qualification.

Triggered from menu.py when user selects Agent role.
Steps: name → region → english → experience → hours → contact
No AI screening — goes directly to admin for manual review.
"""

import logging

from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup, Message

from bot.config import config
from bot.services.followup import APPLICATION_RECEIVED, DECLINE_ENGLISH

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
    name = message.text.strip()
    await state.update_data(name=name)

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
    await message.answer(
        f"Nice to meet you, {name.split()[0]}! 🙂\n\n"
        "Where are you based?",
        reply_markup=keyboard,
    )
    await state.set_state(AgentForm.waiting_region)


# --- Step 2: Region ---

@router.callback_query(AgentForm.waiting_region, F.data.startswith("aregion_"))
async def agent_region(callback: CallbackQuery, state: FSMContext):
    region = callback.data.removeprefix("aregion_")
    await callback.answer()
    await state.update_data(region=region)

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
    await callback.message.answer(
        "What is your English level?\n\n"
        "You'll need at least B1 (Intermediate) to communicate "
        "with candidates and our team.",
        reply_markup=keyboard,
    )
    await state.set_state(AgentForm.waiting_english)


# --- Step 3: English Level ---

@router.callback_query(AgentForm.waiting_english, F.data.startswith("aeng_"))
async def agent_english(callback: CallbackQuery, state: FSMContext):
    level = callback.data.removeprefix("aeng_")
    await callback.answer()

    if level == "beginner":
        await state.update_data(english_level="beginner")
        await callback.message.answer(DECLINE_ENGLISH)
        await state.clear()
        return

    level_map = {"b1": "B1", "b2": "B2", "c1": "C1", "native": "Native"}
    await state.update_data(english_level=level_map.get(level, level))

    await callback.message.answer(
        "Have you done any recruiting, referral work, or network building before?\n\n"
        "Tell us briefly about your experience — it's totally okay if you're new to this!"
    )
    await state.set_state(AgentForm.waiting_experience)


# --- Step 4: Recruiting Experience ---

@router.message(AgentForm.waiting_experience)
async def agent_experience(message: Message, state: FSMContext):
    await state.update_data(recruiting_experience=message.text.strip())

    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="5-10 hrs/week", callback_data="ahours_5-10")],
        [InlineKeyboardButton(text="10-20 hrs/week", callback_data="ahours_10-20")],
        [InlineKeyboardButton(text="20+ hrs/week (full-time)", callback_data="ahours_20+")],
    ])
    await message.answer(
        "How many hours per week can you dedicate to recruiting?",
        reply_markup=keyboard,
    )
    await state.set_state(AgentForm.waiting_hours)


# --- Step 5: Available Hours ---

@router.callback_query(AgentForm.waiting_hours, F.data.startswith("ahours_"))
async def agent_hours(callback: CallbackQuery, state: FSMContext):
    hours = callback.data.removeprefix("ahours_")
    await callback.answer()
    await state.update_data(available_hours=hours)

    await callback.message.answer(
        "Last question! 🙂\n\n"
        "Please share your contact:\n"
        "• Telegram @username (preferred)\n"
        "• Or WhatsApp number"
    )
    await state.set_state(AgentForm.waiting_contact)


# --- Step 6: Contact → Notify Admin ---

@router.message(AgentForm.waiting_contact)
async def agent_contact(message: Message, state: FSMContext):
    await state.update_data(contact_info=message.text.strip())
    data = await state.get_data()
    await state.clear()

    await message.answer(APPLICATION_RECEIVED)
    await _notify_admin_agent(message, data)


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
