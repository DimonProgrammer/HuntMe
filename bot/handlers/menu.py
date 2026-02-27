"""Main menu handler — /start, vacancy info, company info, ask question.

Operator-only flow (Phase 1). Agent and Model flows disabled.
"""

import logging
import re

from datetime import datetime, timedelta

from aiogram import F, Router
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup, Message
from sqlalchemy import select

from bot.config import config
from bot.database import async_session
from bot.database.models import Candidate, FunnelEvent
from bot.handlers.operator_flow import OperatorForm, _track_event
from bot.services import notion_leads

logger = logging.getLogger(__name__)
router = Router()


class MenuStates(StatesGroup):
    main_menu = State()
    waiting_question = State()


# --- Keyboards ---

def _main_menu_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🚀 Apply Now", callback_data="menu_apply")],
        [InlineKeyboardButton(text="💼 About the Vacancy", callback_data="menu_vacancy")],
        [InlineKeyboardButton(text="🏢 About the Company", callback_data="menu_company")],
        [InlineKeyboardButton(text="❓ Ask a Question", callback_data="menu_question")],
    ])


def _back_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="⬅️ Back to Menu", callback_data="back_main")],
    ])


# --- Main menu text ---

MAIN_MENU_TEXT = (
    "Hey! Welcome to Apex Talent 👋\n\n"
    "We hire Live Stream Operators — a behind-the-scenes remote role. "
    "You help streamers with OBS, chat, and scheduling. Never on camera.\n\n"
    "💰 $600-800/month starting, paid in USD\n"
    "📈 Top performers earn $1,500+/month\n"
    "🏠 100% remote, flexible shifts\n"
    "🎓 Paid training — no experience needed\n"
    "🛡 Zero fees — we pay you, never the other way\n\n"
    "Takes 2-3 minutes to apply. Ready?"
)


# --- /start ---

@router.message(F.text.startswith("/start"))
async def cmd_start(message: Message, state: FSMContext):
    await state.clear()

    # Parse deep link: /start <param>
    # land_42 → landing lead, ref_123456 → referral, anything else → UTM source
    parts = message.text.split()
    if len(parts) > 1:
        param = parts[1].strip()
        if param.startswith("land_"):
            # Landing lead → auto-start operator flow (skip menu + name)
            await _handle_landing_deeplink(message, state, param)
            return
        elif param.startswith("ref_"):
            try:
                referrer_id = int(param.removeprefix("ref_"))
                if referrer_id != message.from_user.id:
                    await state.update_data(referrer_tg_id=referrer_id)
                    await _track_event(message.from_user.id, "referral_click", "start", {"referrer_id": referrer_id})
            except ValueError:
                pass
        else:
            # UTM source: fb_ph, jb_ng, landing, ig, tw, etc.
            await state.update_data(utm_source=param)
            await _track_event(message.from_user.id, "utm_source", "start", {"source": param})

    await _track_event(message.from_user.id, "bot_started", "start")

    # Track in Notion
    data = await state.get_data()
    notion_page_id = await notion_leads.on_start(
        tg_id=message.from_user.id,
        tg_username=message.from_user.username,
        utm_source=data.get("utm_source"),
    )
    if notion_page_id:
        await state.update_data(notion_page_id=notion_page_id)

    await message.answer(MAIN_MENU_TEXT, reply_markup=_main_menu_kb())
    await state.set_state(MenuStates.main_menu)


async def _handle_landing_deeplink(message: Message, state: FSMContext, param: str):
    """Landing lead clicked deep link → load name from DB → auto-start screening."""
    from bot.services.followup import WARM_GREETING

    candidate_name = None
    try:
        cid = int(param.removeprefix("land_"))
        async with async_session() as session:
            result = await session.execute(
                select(Candidate).where(Candidate.id == cid)
            )
            candidate = result.scalar_one_or_none()
            if candidate:
                candidate_name = candidate.name
                # Link TG user to existing candidate row
                candidate.tg_user_id = message.from_user.id
                candidate.status = "in_bot"
                await session.commit()
    except (ValueError, Exception) as exc:
        logger.debug("Landing deep link parse error: %s", exc)

    name = candidate_name or message.from_user.first_name or "there"

    await state.update_data(
        utm_source="landing",
        candidate_type="operator",
        name=name,
    )
    await _track_event(message.from_user.id, "bot_started", "start", {"source": "landing"})

    # Track in Notion
    notion_page_id = await notion_leads.on_start(
        tg_id=message.from_user.id,
        tg_username=message.from_user.username,
        utm_source="landing",
    )
    if notion_page_id:
        await state.update_data(notion_page_id=notion_page_id)
        await notion_leads.on_name(notion_page_id, name)

    # Greeting → skip to has_pc (name already known)
    greeting = WARM_GREETING.format(name=name)
    await message.answer(greeting)
    await state.set_state(OperatorForm.waiting_has_pc)
    from bot.handlers.operator_flow import _send_step_prompt
    await _send_step_prompt(message, state)


# --- /referral — generate unique referral link ---

@router.message(F.text == "/referral")
async def cmd_referral(message: Message, state: FSMContext):
    user_id = message.from_user.id
    link = f"https://t.me/apextalent_bot?start=ref_{user_id}"
    await message.answer(
        "Your personal referral link:\n\n"
        f"{link}\n\n"
        "Share it with friends! When someone you refer gets hired, "
        "you earn $50-100 per person.\n\n"
        "The more people you refer, the more you earn:\n"
        "  1-3 hires: $50 each\n"
        "  4-6 hires: $75 each\n"
        "  7+ hires: $100 each"
    )


# --- /menu — return from anywhere ---

@router.message(F.text == "/menu")
async def cmd_menu(message: Message, state: FSMContext):
    await state.clear()
    await message.answer(MAIN_MENU_TEXT, reply_markup=_main_menu_kb())
    await state.set_state(MenuStates.main_menu)


# --- Universal back_main callback (no state filter) ---

@router.callback_query(F.data == "back_main")
async def cb_back_main(callback: CallbackQuery, state: FSMContext):
    await callback.answer()
    await state.clear()
    try:
        await callback.message.edit_text(MAIN_MENU_TEXT, reply_markup=_main_menu_kb())
    except Exception:
        await callback.message.answer(MAIN_MENU_TEXT, reply_markup=_main_menu_kb())
    await state.set_state(MenuStates.main_menu)


# --- /ask — pause flow and ask a question (works from any state) ---

@router.message(Command("ask"))
async def cmd_ask(message: Message, state: FSMContext):
    """Pause current flow, let candidate ask a question via /ask menu command."""
    current = await state.get_state()
    # Save current state so we can resume later
    if current and current != MenuStates.waiting_question.state:
        await state.update_data(paused_state=current)

    resume_kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="▶️ Continue filling", callback_data="resume_form")],
        [InlineKeyboardButton(text="⬅️ Back to Menu", callback_data="back_main")],
    ])
    await state.set_state(MenuStates.waiting_question)
    await message.answer(
        "Type your question and our team will get back to you shortly. 💬\n\n"
        "When you're done, tap 'Continue filling' to resume your application.",
        reply_markup=resume_kb,
    )


# --- Ask a Question ---

@router.callback_query(F.data == "menu_question")
async def cb_menu_question(callback: CallbackQuery, state: FSMContext):
    """Ask a question — works from any state (including Reply button on admin messages)."""
    await callback.answer()
    current = await state.get_state()
    # Save current state so we can resume later (if in a form)
    if current and current != MenuStates.waiting_question.state:
        await state.update_data(paused_state=current)

    data = await state.get_data()
    has_form = data.get("paused_state") is not None

    if has_form:
        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="▶️ Continue filling", callback_data="resume_form")],
            [InlineKeyboardButton(text="⬅️ Back to Menu", callback_data="back_main")],
        ])
    else:
        kb = _back_kb()

    try:
        await callback.message.edit_text(
            "Type your message and our team will get back to you shortly. 💬",
            reply_markup=kb,
        )
    except Exception:
        await callback.message.answer(
            "Type your message and our team will get back to you shortly. 💬",
            reply_markup=kb,
        )
    await state.set_state(MenuStates.waiting_question)


@router.message(MenuStates.waiting_question)
async def process_question(message: Message, state: FSMContext):
    text = message.text.strip() if message.text else ""
    if not text:
        return

    # Forward to admin
    username = message.from_user.username or "N/A"
    first_name = message.from_user.first_name or "Unknown"
    admin_text = (
        f"❓ QUESTION from {first_name} "
        f"(@{username}, ID: {message.from_user.id})\n\n"
        f"{text}\n\n"
        f"Reply to this message to answer."
    )
    try:
        await message.bot.send_message(config.ADMIN_CHAT_ID, admin_text)
    except Exception:
        logger.exception("Failed to forward question to admin")

    data = await state.get_data()
    if data.get("paused_state"):
        # They were in a form — offer to resume
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="▶️ Continue filling", callback_data="resume_form")],
            [InlineKeyboardButton(text="❓ Ask another question", callback_data="menu_question")],
        ])
        await message.answer(
            "Thanks! Our team will reply shortly. 🙂\n\n"
            "Tap 'Continue filling' to resume your application.",
            reply_markup=keyboard,
        )
    else:
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="❓ Ask another question", callback_data="menu_question")],
            [InlineKeyboardButton(text="🚀 Apply Now", callback_data="menu_apply")],
            [InlineKeyboardButton(text="⬅️ Back to Menu", callback_data="back_main")],
        ])
        await message.answer(
            "Thanks for your question! 🙂\n\n"
            "Our team will get back to you shortly. "
            "You'll receive a reply right here in this chat.",
            reply_markup=keyboard,
        )
    await state.set_state(MenuStates.main_menu)


# --- Resume form from /ask or reminder ---

@router.callback_query(F.data == "resume_form")
async def cb_resume_form(callback: CallbackQuery, state: FSMContext):
    """Resume the paused form flow."""
    await callback.answer()
    data = await state.get_data()
    paused = data.get("paused_state")

    if not paused:
        # No saved state — go to main menu
        await state.clear()
        try:
            await callback.message.edit_text(MAIN_MENU_TEXT, reply_markup=_main_menu_kb())
        except Exception:
            await callback.message.answer(MAIN_MENU_TEXT, reply_markup=_main_menu_kb())
        await state.set_state(MenuStates.main_menu)
        return

    # Restore the saved state
    await state.update_data(paused_state=None)
    await state.set_state(paused)

    try:
        await callback.message.edit_text("Great, let's continue! 🙂")
    except Exception:
        pass

    if paused.startswith("OperatorForm:"):
        from bot.handlers.operator_flow import _send_step_prompt
        await _send_step_prompt(callback, state)
    elif paused.startswith("InterviewBooking:"):
        step = paused.split(":")[-1]
        prompts = {
            "waiting_birth_date": (
                "What is your date of birth?\n"
                "Please enter in format: DD.MM.YYYY (e.g. 15.05.1998)"
            ),
            "waiting_phone": (
                "What is your phone number (with country code)?\n"
                "For example: +639171234567"
            ),
            "waiting_experience": (
                "Do you have any experience with live streaming, "
                "moderation, customer service, or other remote work?\n\n"
                "If yes, briefly describe. If no, say 'no experience'."
            ),
        }
        prompt = prompts.get(step, "Please continue with the question above.")
        await callback.message.answer(prompt)
    else:
        await callback.message.answer("Let's continue from where you left off!")


# --- Reminder callbacks (from reminder.py background task) ---

@router.callback_query(F.data.startswith("remind_"))
async def on_reminder_choice(callback: CallbackQuery, state: FSMContext):
    """Handle reminder time choice or 'Continue filling' from reminder prompt."""
    await callback.answer()
    choice = callback.data.removeprefix("remind_")

    if choice == "continue":
        # Resume current step
        current = await state.get_state()
        await state.update_data(
            reminder_prompt_sent_at=None,
            reminder_scheduled_at=None,
        )
        try:
            await callback.message.edit_text("Great, let's continue! 🙂")
        except Exception:
            pass
        if current and current.startswith("OperatorForm:"):
            from bot.handlers.operator_flow import _send_step_prompt
            await _send_step_prompt(callback, state)
        elif current and current.startswith("InterviewBooking:"):
            step = current.split(":")[-1]
            prompts = {
                "waiting_birth_date": "What is your date of birth? (DD.MM.YYYY)",
                "waiting_phone": "What is your phone number with country code?",
                "waiting_experience": "Any experience with streaming, moderation, or remote work?",
            }
            prompt = prompts.get(step, "Please continue with the question above.")
            await callback.message.answer(prompt)
        else:
            await callback.message.answer("Let's continue!")
        return

    # Time choice: remind_30, remind_60, remind_180, remind_720
    try:
        minutes = int(choice)
    except ValueError:
        return

    remind_at = datetime.utcnow() + timedelta(minutes=minutes)
    await state.update_data(reminder_scheduled_at=remind_at.isoformat())

    time_labels = {30: "30 minutes", 60: "1 hour", 180: "3 hours", 720: "12 hours"}
    label = time_labels.get(minutes, f"{minutes} minutes")

    await callback.answer(f"Got it! I'll remind you in {label} 🔔")
    try:
        await callback.message.edit_text(
            f"Got it! I'll remind you in {label}. See you soon! 👋"
        )
    except Exception:
        pass


# --- Apply Now → check duplicate → operator flow ---

@router.callback_query(MenuStates.main_menu, F.data == "menu_apply")
async def cb_menu_apply(callback: CallbackQuery, state: FSMContext):
    await callback.answer()
    user_id = callback.from_user.id

    # Check if candidate already applied
    try:
        async with async_session() as session:
            result = await session.execute(
                select(Candidate).where(Candidate.tg_user_id == user_id)
            )
            existing = result.scalar_one_or_none()

        if existing:
            status_labels = {
                "new": "under review",
                "screened": "screened, waiting for decision",
                "interview_invited": "interview scheduled",
                "active": "active operator",
                "declined": "declined",
                "churned": "inactive",
            }
            status_text = status_labels.get(existing.status, existing.status)
            keyboard = InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="🔄 Start new application", callback_data="reapply")],
                [InlineKeyboardButton(text="⬅️ Back to Menu", callback_data="back_main")],
            ])
            try:
                await callback.message.edit_text(
                    f"Hey {existing.name.split()[0]}! 👋\n\n"
                    f"You've already applied. Your current status: {status_text}.\n\n"
                    "Would you like to start a new application?",
                    reply_markup=keyboard,
                )
            except Exception:
                await callback.message.answer(
                    f"Hey {existing.name.split()[0]}! 👋\n\n"
                    f"You've already applied. Your current status: {status_text}.\n\n"
                    "Would you like to start a new application?",
                    reply_markup=keyboard,
                )
            return
    except Exception:
        logger.debug("DB check failed — proceeding without duplicate check")

    # No duplicate — start operator flow
    await _track_event(callback.from_user.id, "button_clicked", "apply_now")
    await _start_operator_flow(callback, state)


@router.callback_query(F.data == "reapply")
async def cb_reapply(callback: CallbackQuery, state: FSMContext):
    await callback.answer()

    # Delete old application
    try:
        async with async_session() as session:
            result = await session.execute(
                select(Candidate).where(Candidate.tg_user_id == callback.from_user.id)
            )
            existing = result.scalar_one_or_none()
            if existing:
                await session.delete(existing)
                await session.commit()
    except Exception:
        logger.debug("Failed to delete old application")

    await _start_operator_flow(callback, state)


async def _start_operator_flow(callback: CallbackQuery, state: FSMContext):
    """Send operator greeting and enter the flow."""
    await state.update_data(candidate_type="operator")
    from bot.services.followup import WARM_GREETING
    greeting = WARM_GREETING.format(name=callback.from_user.first_name or "there")
    try:
        await callback.message.edit_text(greeting)
    except Exception:
        await callback.message.answer(greeting)
    await state.set_state(OperatorForm.waiting_name)


# --- Apply shortcut from vacancy info ---

@router.callback_query(F.data == "apply_from_info")
async def cb_apply_from_info(callback: CallbackQuery, state: FSMContext):
    await callback.answer()
    await _start_operator_flow(callback, state)


# --- About the Vacancy ---

@router.callback_query(MenuStates.main_menu, F.data == "menu_vacancy")
async def cb_menu_vacancy(callback: CallbackQuery, state: FSMContext):
    await callback.answer()
    text = (
        "LIVE STREAM OPERATOR\n\n"
        "What you'll do:\n"
        "  • Set up streaming software (OBS) and manage stream tech\n"
        "  • Moderate live chats during broadcasts\n"
        "  • Schedule and organize streaming sessions\n"
        "  • Provide technical support to content creators\n"
        "  • You NEVER appear on camera — fully behind the scenes\n\n"
        "Compensation:\n"
        "  • Starting: $600-800/month\n"
        "  • After 1-2 months: $1,000-1,200/month\n"
        "  • Top performers: $1,500+/month\n"
        "  • Paid training: 5-7 days, $30 per shift\n"
        "  • All payments in USD\n\n"
        "Schedule:\n"
        "  • 5 days/week, 2 days off\n"
        "  • 6-8 hours/day\n"
        "  • 4 shift options: morning / day / evening / night\n"
        "  • Payment every Sunday in USD\n\n"
        "Requirements:\n"
        "  • Windows PC or laptop (MacBooks not supported)\n"
        "  • CPU: Intel Core i3 10th gen+ or AMD Ryzen 3 3000+\n"
        "  • GPU: NVIDIA GTX 1060 6GB+ or AMD RX 5500+\n"
        "  • Internet: 100 Mbps+\n"
        "  • English: B1 (Intermediate) minimum\n"
        "  • Age: 18+"
    )
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🚀 Apply Now", callback_data="apply_from_info")],
        [InlineKeyboardButton(text="⬅️ Back to Menu", callback_data="back_main")],
    ])
    try:
        await callback.message.edit_text(text, reply_markup=keyboard)
    except Exception:
        await callback.message.answer(text, reply_markup=keyboard)


# --- About the Company ---

@router.callback_query(MenuStates.main_menu, F.data == "menu_company")
async def cb_menu_company(callback: CallbackQuery, state: FSMContext):
    await callback.answer()
    text = (
        "ABOUT APEX TALENT\n\n"
        "We're an international talent management agency that works "
        "with content creators on streaming platforms.\n\n"
        "What we do:\n"
        "  • Connect talented people with streaming opportunities worldwide\n"
        "  • Provide full training and ongoing support for every team member\n"
        "  • Handle the technical side so creators can focus on content\n\n"
        "Our team:\n"
        "  • Operating in 15+ countries\n"
        "  • 100% remote — work from anywhere\n"
        "  • Payment every Sunday in USD, without exception\n"
        "  • Dedicated mentor for every new team member\n\n"
        "We never ask for upfront payments.\n"
        "Your first earnings start during paid training ($30/shift, 5-7 days)."
    )
    try:
        await callback.message.edit_text(text, reply_markup=_back_kb())
    except Exception:
        await callback.message.answer(text, reply_markup=_back_kb())


# --- Catch-all: forward free text in main_menu to admin (enables continuous chat) ---

@router.message(MenuStates.main_menu, F.text)
async def forward_text_to_admin(message: Message, state: FSMContext):
    """Any text typed in main menu → forwarded to admin as a message."""
    text = message.text.strip() if message.text else ""
    if not text or text.startswith("/"):
        return

    username = message.from_user.username or "N/A"
    first_name = message.from_user.first_name or "Unknown"
    admin_text = (
        f"💬 MESSAGE from {first_name} "
        f"(@{username}, ID: {message.from_user.id})\n\n"
        f"{text}\n\n"
        f"Reply to this message to answer."
    )
    try:
        await message.bot.send_message(config.ADMIN_CHAT_ID, admin_text)
    except Exception:
        logger.exception("Failed to forward message to admin")
        await message.answer("Sorry, something went wrong. Please try again.")
        return

    await message.answer(
        "Message sent! Our team will reply shortly. 💬",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🚀 Apply Now", callback_data="menu_apply")],
            [InlineKeyboardButton(text="⬅️ Back to Menu", callback_data="back_main")],
        ]),
    )
