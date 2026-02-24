"""7-step FSM flow for Content Creator (Model) qualification.

Triggered from menu.py when user selects Model role.
Steps: name → age → region → english → platform experience → schedule → contact
No AI screening — goes directly to admin for manual review.
"""

import logging

from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup, Message

from bot.config import config
from bot.services.followup import APPLICATION_RECEIVED, DECLINE_UNDERAGE

logger = logging.getLogger(__name__)
router = Router()


class ModelForm(StatesGroup):
    waiting_name = State()
    waiting_age = State()
    waiting_region = State()
    waiting_english = State()
    waiting_platform_experience = State()
    waiting_schedule = State()
    waiting_contact = State()


# --- Step 1: Name ---

@router.message(ModelForm.waiting_name)
async def model_name(message: Message, state: FSMContext):
    name = message.text.strip()
    await state.update_data(name=name)

    await message.answer(
        f"Nice to meet you, {name.split()[0]}! 🙂\n\n"
        "How old are you?"
    )
    await state.set_state(ModelForm.waiting_age)


# --- Step 2: Age ---

@router.message(ModelForm.waiting_age)
async def model_age(message: Message, state: FSMContext):
    text = message.text.strip()

    age = None
    for word in text.split():
        if word.isdigit():
            age = int(word)
            break

    if age is None:
        try:
            age = int(text)
        except ValueError:
            await message.answer("Please enter your age as a number (e.g., 22).")
            return

    if age < 18:
        await state.update_data(age=age)
        await message.answer(DECLINE_UNDERAGE)
        await state.clear()
        return

    await state.update_data(age=age)

    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="Philippines", callback_data="mregion_ph"),
            InlineKeyboardButton(text="Nigeria", callback_data="mregion_ng"),
        ],
        [
            InlineKeyboardButton(text="Latin America", callback_data="mregion_latam"),
            InlineKeyboardButton(text="RU / CIS", callback_data="mregion_ru"),
        ],
        [InlineKeyboardButton(text="Other", callback_data="mregion_other")],
    ])
    await message.answer(
        "Where are you based?",
        reply_markup=keyboard,
    )
    await state.set_state(ModelForm.waiting_region)


# --- Step 3: Region ---

@router.callback_query(ModelForm.waiting_region, F.data.startswith("mregion_"))
async def model_region(callback: CallbackQuery, state: FSMContext):
    region = callback.data.removeprefix("mregion_")
    await callback.answer()
    await state.update_data(region=region)

    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="Beginner (A1-A2)", callback_data="meng_beginner"),
            InlineKeyboardButton(text="Intermediate (B1)", callback_data="meng_b1"),
        ],
        [
            InlineKeyboardButton(text="Upper-Intermediate (B2)", callback_data="meng_b2"),
            InlineKeyboardButton(text="Advanced (C1+)", callback_data="meng_c1"),
        ],
        [InlineKeyboardButton(text="Native / Fluent", callback_data="meng_native")],
    ])
    await callback.message.answer(
        "What is your English level?",
        reply_markup=keyboard,
    )
    await state.set_state(ModelForm.waiting_english)


# --- Step 4: English Level ---

@router.callback_query(ModelForm.waiting_english, F.data.startswith("meng_"))
async def model_english(callback: CallbackQuery, state: FSMContext):
    level = callback.data.removeprefix("meng_")
    await callback.answer()

    level_map = {"beginner": "A1-A2", "b1": "B1", "b2": "B2", "c1": "C1", "native": "Native"}
    await state.update_data(english_level=level_map.get(level, level))

    await callback.message.answer(
        "Have you ever streamed or created content on platforms like "
        "Twitch, YouTube, TikTok, or similar?\n\n"
        "Tell us a bit about your experience — it's completely fine if you're just starting out!"
    )
    await state.set_state(ModelForm.waiting_platform_experience)


# --- Step 5: Platform Experience ---

@router.message(ModelForm.waiting_platform_experience)
async def model_platform_experience(message: Message, state: FSMContext):
    await state.update_data(platform_experience=message.text.strip())

    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Morning (6:00-12:00)", callback_data="msched_morning")],
        [InlineKeyboardButton(text="Day (12:00-18:00)", callback_data="msched_day")],
        [InlineKeyboardButton(text="Evening (18:00-00:00)", callback_data="msched_evening")],
        [InlineKeyboardButton(text="Night (00:00-6:00)", callback_data="msched_night")],
        [InlineKeyboardButton(text="Flexible / Multiple shifts", callback_data="msched_flexible")],
    ])
    await message.answer(
        "What shift would work best for you?",
        reply_markup=keyboard,
    )
    await state.set_state(ModelForm.waiting_schedule)


# --- Step 6: Schedule ---

@router.callback_query(ModelForm.waiting_schedule, F.data.startswith("msched_"))
async def model_schedule(callback: CallbackQuery, state: FSMContext):
    sched = callback.data.removeprefix("msched_")
    await callback.answer()

    sched_map = {
        "morning": "Morning (6:00-12:00)",
        "day": "Day (12:00-18:00)",
        "evening": "Evening (18:00-00:00)",
        "night": "Night (00:00-6:00)",
        "flexible": "Flexible",
    }
    await state.update_data(preferred_schedule=sched_map.get(sched, sched))

    await callback.message.answer(
        "Last question! 🙂\n\n"
        "Please share your contact:\n"
        "• Telegram @username (preferred)\n"
        "• Or WhatsApp number"
    )
    await state.set_state(ModelForm.waiting_contact)


# --- Step 7: Contact → Notify Admin ---

@router.message(ModelForm.waiting_contact)
async def model_contact(message: Message, state: FSMContext):
    await state.update_data(contact_info=message.text.strip())
    data = await state.get_data()
    await state.clear()

    await message.answer(APPLICATION_RECEIVED)
    await _notify_admin_model(message, data)


async def _notify_admin_model(message: Message, data: dict):
    region_map = {
        "ph": "Philippines",
        "ng": "Nigeria",
        "latam": "Latin America",
        "ru": "RU / CIS",
        "other": "Other",
    }
    region_label = region_map.get(data.get("region", "other"), data.get("region", "N/A"))

    admin_text = (
        "[MODEL APPLICATION]\n\n"
        f"Name: {data.get('name', 'N/A')}\n"
        f"TG: @{message.from_user.username or 'N/A'} (ID: {message.from_user.id})\n"
        f"Age: {data.get('age', 'N/A')}\n"
        f"Region: {region_label}\n"
        f"English: {data.get('english_level', 'N/A')}\n"
        f"Platform Experience: {data.get('platform_experience', 'N/A')}\n"
        f"Preferred Schedule: {data.get('preferred_schedule', 'N/A')}\n"
        f"Contact: {data.get('contact_info', 'N/A')}"
    )
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="✅ Approve Model", callback_data=f"modelok_{message.from_user.id}"),
            InlineKeyboardButton(text="❌ Reject", callback_data=f"modelno_{message.from_user.id}"),
        ],
    ])
    try:
        await message.bot.send_message(config.ADMIN_CHAT_ID, admin_text, reply_markup=keyboard)
    except Exception:
        logger.exception("Failed to notify admin about model application")
