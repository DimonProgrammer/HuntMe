"""FSM flow for candidate application via Telegram bot."""

import logging

import aiohttp
from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup, Message

from bot.config import config
from bot.services.screener import screen_candidate

logger = logging.getLogger(__name__)
router = Router()


class ApplicationForm(StatesGroup):
    waiting_name = State()
    waiting_experience = State()
    waiting_english = State()
    waiting_availability = State()
    waiting_rate = State()


@router.message(F.text == "/start")
async def cmd_start(message: Message, state: FSMContext):
    # Skip if this is the admin
    if message.from_user.id == config.ADMIN_CHAT_ID:
        return

    await message.answer(
        "Welcome! We're hiring Remote Chat Moderators.\n\n"
        "I'll ask you a few quick questions to see if you're a good fit.\n"
        "It takes less than 2 minutes.\n\n"
        "What is your full name?"
    )
    await state.set_state(ApplicationForm.waiting_name)


@router.message(ApplicationForm.waiting_name)
async def process_name(message: Message, state: FSMContext):
    await state.update_data(name=message.text)
    await message.answer(
        "Great! Do you have any experience in admin, customer support, "
        "virtual assistant, or similar online work?\n\n"
        "Tell me briefly (or type 'No experience' if none)."
    )
    await state.set_state(ApplicationForm.waiting_experience)


@router.message(ApplicationForm.waiting_experience)
async def process_experience(message: Message, state: FSMContext):
    await state.update_data(experience=message.text)
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Beginner", callback_data="eng_beginner")],
        [InlineKeyboardButton(text="Intermediate", callback_data="eng_intermediate")],
        [InlineKeyboardButton(text="Advanced", callback_data="eng_advanced")],
        [InlineKeyboardButton(text="Native / Fluent", callback_data="eng_native")],
    ])
    await message.answer("How would you rate your English level?", reply_markup=keyboard)
    await state.set_state(ApplicationForm.waiting_english)


@router.callback_query(ApplicationForm.waiting_english, F.data.startswith("eng_"))
async def process_english(callback: CallbackQuery, state: FSMContext):
    level = callback.data.removeprefix("eng_")
    await state.update_data(english_level=level)
    await callback.message.answer(
        "How many hours per day can you work?\n"
        "(e.g., '6 hours, flexible schedule' or 'full-time 8 hours')"
    )
    await state.set_state(ApplicationForm.waiting_availability)
    await callback.answer()


@router.message(ApplicationForm.waiting_availability)
async def process_availability(message: Message, state: FSMContext):
    await state.update_data(availability=message.text)
    await message.answer(
        "Last question: what is your expected monthly salary in USD?\n"
        "(e.g., '$300', '$500', 'flexible')"
    )
    await state.set_state(ApplicationForm.waiting_rate)


@router.message(ApplicationForm.waiting_rate)
async def process_rate(message: Message, state: FSMContext):
    await state.update_data(expected_rate=message.text)
    data = await state.get_data()
    await state.clear()

    await message.answer("Thank you! Reviewing your application now...")

    # Screen with Claude
    result = await screen_candidate(
        name=data["name"],
        experience=data.get("experience", "N/A"),
        english_level=data.get("english_level", "N/A"),
        availability=data.get("availability", "N/A"),
        expected_rate=data.get("expected_rate", "N/A"),
        message=f"Telegram user @{message.from_user.username or 'no_username'}",
    )

    # Send response to candidate
    await message.answer(result.suggested_response)

    # Notify admin
    status_icon = {"PASS": "GREEN", "MAYBE": "YELLOW", "REJECT": "RED"}.get(result.recommendation, "?")
    admin_text = (
        f"[{status_icon}] {result.recommendation}\n\n"
        f"Name: {data['name']}\n"
        f"TG: @{message.from_user.username or 'N/A'} (ID: {message.from_user.id})\n"
        f"Score: {result.overall_score}/100\n"
        f"English: {result.english_score}/10 | Experience: {result.experience_score}/10\n"
        f"Availability: {result.availability_score}/10 | Equipment: {result.equipment_score}/10\n"
        f"Motivation: {result.motivation_score}/10\n\n"
        f"Reasoning: {result.reasoning}"
    )

    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="Send Referral Link", callback_data=f"ref_{message.from_user.id}"),
            InlineKeyboardButton(text="Reject", callback_data=f"rej_{message.from_user.id}"),
        ],
    ])

    try:
        await message.bot.send_message(config.ADMIN_CHAT_ID, admin_text, reply_markup=keyboard)
    except Exception:
        logger.exception("Failed to notify admin")

    # Send to n8n webhook (non-blocking)
    try:
        async with aiohttp.ClientSession() as session:
            await session.post(
                f"{config.N8N_WEBHOOK_URL}/new-application",
                json={
                    "telegram_user_id": message.from_user.id,
                    "telegram_username": message.from_user.username,
                    **data,
                    "score": result.overall_score,
                    "recommendation": result.recommendation,
                },
                timeout=aiohttp.ClientTimeout(total=5),
            )
    except Exception:
        logger.debug("n8n webhook not available — skipping")
