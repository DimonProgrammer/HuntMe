"""Main menu handler — /start, vacancy info, company info, ask question.

Operator-only flow (Phase 1). Agent and Model flows disabled.
"""

import logging
import re
from typing import Optional

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
from bot.messages import msg, detect_lang_from_deeplink
from bot.services import notion_leads

logger = logging.getLogger(__name__)
router = Router()


class MenuStates(StatesGroup):
    main_menu = State()
    waiting_question = State()


# --- Keyboards ---

def _main_menu_kb(lang: str = "en") -> InlineKeyboardMarkup:
    m = msg(lang)
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=m.BTN_APPLY, callback_data="menu_apply")],
        [InlineKeyboardButton(text=m.BTN_VACANCY, callback_data="menu_vacancy")],
        [InlineKeyboardButton(text=m.BTN_COMPANY, callback_data="menu_company")],
        [InlineKeyboardButton(text=m.BTN_QUESTION, callback_data="menu_question")],
    ])


def _back_kb(lang: str = "en") -> InlineKeyboardMarkup:
    m = msg(lang)
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=m.BTN_BACK_MENU, callback_data="back_main")],
    ])


# --- Helpers ---

def _get_lang(data: dict) -> str:
    """Get language from FSM state data."""
    return data.get("language", "en")


def _format_slot(slot: str, lang: str) -> str:
    """Format '05.03.2026 18:00' → '5 марта в 18:00' (ru) or 'March 5 at 18:00' (en)."""
    try:
        dt = datetime.strptime(slot, "%d.%m.%Y %H:%M")
        if lang == "ru":
            months_ru = ["янв", "фев", "мар", "апр", "мая", "июн",
                         "июл", "авг", "сен", "окт", "ноя", "дек"]
            return f"{dt.day} {months_ru[dt.month - 1]} в {dt.strftime('%H:%M')}"
        else:
            return dt.strftime("%-d %B at %H:%M")
    except Exception:
        return slot


async def _build_status_banner(
    tg_user_id: int, fsm_data: dict, lang: str
) -> Optional[tuple]:
    """Return (text, keyboard | None) status banner for main menu, or None if nothing to show."""
    m = msg(lang)
    paused = fsm_data.get("paused_state")

    # Active form in progress → offer Continue button
    if paused:
        if paused.startswith("OperatorForm:") or paused.startswith("AgentForm:") or paused.startswith("ModelForm:"):
            kb = InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text=m.BTN_CONTINUE, callback_data="resume_form")],
            ])
            return (m.STATUS_FORM_IN_PROGRESS, kb)

        if paused.startswith("InterviewBooking:"):
            step = paused.split(":")[-1]
            if step == "waiting_crm_approval":
                return (m.STATUS_INTERVIEW_PENDING, None)
            elif step == "waiting_slot_notify":
                return (m.STATUS_WAITING_SLOT, None)
            else:
                kb = InlineKeyboardMarkup(inline_keyboard=[
                    [InlineKeyboardButton(text=m.BTN_CONTINUE, callback_data="resume_form")],
                ])
                return (m.STATUS_BOOKING_IN_PROGRESS, kb)

    # No active FSM form → check DB for persistent statuses
    try:
        async with async_session() as session:
            result = await session.execute(
                select(Candidate).where(Candidate.tg_user_id == tg_user_id)
            )
            candidate = result.scalar_one_or_none()
    except Exception:
        return None

    if not candidate:
        return None

    # Interview confirmed
    if candidate.interview_confirmed == "confirmed" and candidate.huntme_crm_slot:
        slot_fmt = _format_slot(candidate.huntme_crm_slot, lang)
        return (m.STATUS_INTERVIEW_CONFIRMED.format(slot=slot_fmt), None)

    # Interview cancelled
    if candidate.interview_confirmed == "cancelled":
        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text=m.BTN_QUESTION, callback_data="menu_question")],
        ])
        return (m.STATUS_INTERVIEW_CANCELLED, kb)

    # Interview scheduled (slot booked, waiting for candidate confirmation)
    if candidate.status == "interview_invited" and candidate.huntme_crm_slot:
        slot_fmt = _format_slot(candidate.huntme_crm_slot, lang)
        return (m.STATUS_INTERVIEW_SCHEDULED.format(slot=slot_fmt), None)

    # In queue for a slot
    if candidate.waiting_for_slot:
        return (m.STATUS_WAITING_SLOT, None)

    # Pending admin decision (MAYBE)
    if candidate.status == "screened" and candidate.recommendation == "MAYBE":
        return (m.STATUS_UNDER_REVIEW, None)

    return None


# --- /start ---

@router.message(F.text.startswith("/start"))
async def cmd_start(message: Message, state: FSMContext):
    # Capture current state BEFORE clearing — needed for status banner
    prev_state = await state.get_state()
    prev_data = await state.get_data()

    lang = None  # will be resolved below

    # Parse deep link: /start <param>
    # land_ru_42 → RU landing lead, land_42 → EN landing lead,
    # ref_123456 → referral, anything else → UTM source
    parts = message.text.split()
    if len(parts) > 1:
        param = parts[1].strip()
        if param.startswith("agent_"):
            # Agent landing lead → auto-start agent flow (skip menu)
            await _handle_agent_deeplink(message, state, param)
            return
        elif param.startswith("model_"):
            # Model deep link → auto-start model flow
            await _handle_model_deeplink(message, state, param)
            return
        elif param.startswith("land_"):
            # Landing lead → auto-start operator flow (skip menu + name)
            lang = detect_lang_from_deeplink(param)
            await _handle_landing_deeplink(message, state, param, lang)
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

    if lang is None:
        lang = prev_data.get("language", "en")

    # Determine if user had an active form (preserve so resume_form callback still works).
    # Also handle the case where user was in waiting_question with a paused form step.
    _form_prefixes = ("OperatorForm:", "InterviewBooking:", "AgentForm:", "ModelForm:")
    prev_paused = prev_data.get("paused_state")
    is_active_form = (
        prev_state and any(prev_state.startswith(p) for p in _form_prefixes)
    ) or (
        prev_paused and any(prev_paused.startswith(p) for p in _form_prefixes)
    )

    await state.clear()

    if is_active_form:
        # Preserve all form data so resume_form can restore the exact step.
        # If prev_state was waiting_question, keep the existing paused_state from data.
        preserved = dict(prev_data)
        preserved["language"] = lang
        if prev_state and any(prev_state.startswith(p) for p in _form_prefixes):
            preserved["paused_state"] = prev_state
        # else: prev_paused already in preserved dict from prev_data
        await state.update_data(**preserved)
    else:
        await state.update_data(language=lang)

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

    m = msg(lang)
    await message.answer(m.MAIN_MENU_TEXT, reply_markup=_main_menu_kb(lang))
    await state.set_state(MenuStates.main_menu)

    # Show contextual status banner if user has an ongoing application
    fresh_data = await state.get_data()
    banner = await _build_status_banner(message.from_user.id, fresh_data, lang)
    if banner:
        text, kb = banner
        await message.answer(text, reply_markup=kb, parse_mode="Markdown")


async def _handle_landing_deeplink(
    message: Message, state: FSMContext, param: str, lang: Optional[str] = None,
):
    """Landing lead clicked deep link → load name from DB → auto-start screening."""
    # Parse candidate ID: land_ru_42 or land_42
    raw_id = param.removeprefix("land_ru_").removeprefix("land_")
    if lang is None:
        lang = "ru" if param.startswith("land_ru_") else "en"
    m = msg(lang)

    candidate_name = None
    try:
        cid = int(raw_id)
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
                candidate.language = lang
                await session.commit()
    except (ValueError, Exception) as exc:
        logger.debug("Landing deep link parse error: %s", exc)

    fallback_name = "друг" if lang == "ru" else "there"
    name = candidate_name or message.from_user.first_name or fallback_name

    await state.update_data(
        utm_source="landing",
        candidate_type="operator",
        name=name,
        language=lang,
    )
    await _track_event(message.from_user.id, "bot_started", "start", {"source": "landing", "lang": lang})

    # Track in Notion
    notion_page_id = await notion_leads.on_start(
        tg_id=message.from_user.id,
        tg_username=message.from_user.username,
        utm_source="landing",
    )
    if notion_page_id:
        await state.update_data(notion_page_id=notion_page_id)
        await notion_leads.on_name(notion_page_id, name)

    # Greeting → skip to has_pc (name already known, no name question)
    greeting = m.WARM_GREETING_LANDING.format(name=name)
    await message.answer(greeting)
    await state.set_state(OperatorForm.waiting_has_pc)
    from bot.handlers.operator_flow import _send_step_prompt
    await _send_step_prompt(message, state)


async def _handle_model_deeplink(
    message: Message, state: FSMContext, param: str,
) -> None:
    """Model deep link clicked → load name from DB if available → auto-start model flow."""
    raw_id = param.removeprefix("model_")
    lang = "en"
    m = msg(lang)

    candidate_name = None
    try:
        cid = int(raw_id)
        async with async_session() as session:
            result = await session.execute(
                select(Candidate).where(Candidate.id == cid)
            )
            candidate = result.scalar_one_or_none()
            if candidate:
                candidate_name = candidate.name
                candidate.tg_user_id = message.from_user.id
                candidate.status = "in_bot"
                candidate.language = lang
                candidate.candidate_type = "model"
                await session.commit()
    except (ValueError, Exception) as exc:
        logger.debug("Model deep link parse error: %s", exc)

    name = candidate_name or message.from_user.first_name or "there"

    await state.update_data(
        utm_source="model_landing",
        candidate_type="model",
        name=name,
        language=lang,
    )
    await _track_event(
        message.from_user.id, "bot_started", "start",
        {"source": "model_landing", "lang": lang},
    )

    # Track in Notion
    notion_page_id = await notion_leads.on_start(
        tg_id=message.from_user.id,
        tg_username=message.from_user.username,
        utm_source="model_landing",
    )
    if notion_page_id:
        await state.update_data(notion_page_id=notion_page_id)
        await notion_leads.on_name(notion_page_id, name)

    # Greeting → start model flow from age (name already known)
    from bot.handlers.model_flow import ModelForm
    greeting = m.MODEL_WELCOME_LANDING.format(name=name)
    await message.answer(greeting)
    await state.set_state(ModelForm.waiting_age)
    from bot.handlers.model_flow import _send_step_prompt
    await _send_step_prompt(message, state)


async def _handle_agent_deeplink(
    message: Message, state: FSMContext, param: str,
) -> None:
    """Agent landing lead clicked deep link → load name from DB → auto-start agent flow."""
    raw_id = param.removeprefix("agent_")
    lang = "en"
    m = msg(lang)

    candidate_name = None
    try:
        cid = int(raw_id)
        async with async_session() as session:
            result = await session.execute(
                select(Candidate).where(Candidate.id == cid)
            )
            candidate = result.scalar_one_or_none()
            if candidate:
                candidate_name = candidate.name
                candidate.tg_user_id = message.from_user.id
                candidate.status = "in_bot"
                candidate.language = lang
                candidate.candidate_type = "agent"
                await session.commit()
    except (ValueError, Exception) as exc:
        logger.debug("Agent deep link parse error: %s", exc)

    name = candidate_name or message.from_user.first_name or "there"

    await state.update_data(
        utm_source="agent_landing",
        candidate_type="agent",
        name=name,
        language=lang,
    )
    await _track_event(
        message.from_user.id, "bot_started", "start",
        {"source": "agent_landing", "lang": lang},
    )

    # Track in Notion
    notion_page_id = await notion_leads.on_start(
        tg_id=message.from_user.id,
        tg_username=message.from_user.username,
        utm_source="agent_landing",
    )
    if notion_page_id:
        await state.update_data(notion_page_id=notion_page_id)
        await notion_leads.on_name(notion_page_id, name)

    # Greeting → skip directly into agent presentation (name known)
    from bot.handlers.agent_flow import AgentForm, send_agent_presentation
    greeting = m.AGENT_GREETING_LANDING.format(name=name)
    await message.answer(greeting)
    await send_agent_presentation(message.bot, message.chat.id, lang)
    await state.set_state(AgentForm.waiting_ready_check)


# --- /referral — generate unique referral link ---

@router.message(F.text == "/referral")
async def cmd_referral(message: Message, state: FSMContext):
    data = await state.get_data()
    lang = _get_lang(data)
    m = msg(lang)
    user_id = message.from_user.id
    link = f"https://t.me/apextalent_bot?start=ref_{user_id}"
    await message.answer(m.REFERRAL_TEXT.format(link=link))


# --- /menu — return from anywhere ---

@router.message(F.text == "/menu")
async def cmd_menu(message: Message, state: FSMContext):
    data = await state.get_data()
    lang = _get_lang(data)
    paused = data.get("paused_state")
    _form_prefixes = ("OperatorForm:", "InterviewBooking:", "AgentForm:", "ModelForm:")
    # Also check if current state is a form (e.g., user types /menu mid-form)
    current = await state.get_state()
    if current and any(current.startswith(p) for p in _form_prefixes):
        paused = current  # treat active form state as the one to preserve
    await state.clear()
    update: dict = {"language": lang}
    if paused and any(paused.startswith(p) for p in _form_prefixes):
        update["paused_state"] = paused
    await state.update_data(**update)
    m = msg(lang)
    await message.answer(m.MAIN_MENU_TEXT, reply_markup=_main_menu_kb(lang))
    await state.set_state(MenuStates.main_menu)
    # Show banner if form was paused
    if update.get("paused_state"):
        fresh_data = await state.get_data()
        banner = await _build_status_banner(message.from_user.id, fresh_data, lang)
        if banner:
            text, kb = banner
            await message.answer(text, reply_markup=kb, parse_mode="Markdown")


# --- Universal back_main callback (no state filter) ---

@router.callback_query(F.data == "back_main")
async def cb_back_main(callback: CallbackQuery, state: FSMContext):
    await callback.answer()
    data = await state.get_data()
    lang = _get_lang(data)
    paused = data.get("paused_state")
    _form_prefixes = ("OperatorForm:", "InterviewBooking:", "AgentForm:", "ModelForm:")
    await state.clear()
    update: dict = {"language": lang}
    if paused and any(paused.startswith(p) for p in _form_prefixes):
        update["paused_state"] = paused
    await state.update_data(**update)
    m = msg(lang)
    try:
        await callback.message.edit_text(m.MAIN_MENU_TEXT, reply_markup=_main_menu_kb(lang))
    except Exception:
        await callback.message.answer(m.MAIN_MENU_TEXT, reply_markup=_main_menu_kb(lang))
    await state.set_state(MenuStates.main_menu)


# --- /continue — resume active application or show current status ---

@router.message(Command("continue"))
async def cmd_continue(message: Message, state: FSMContext):
    data = await state.get_data()
    lang = _get_lang(data)
    m = msg(lang)
    current = await state.get_state()

    # States where the bot is waiting for external action — show status, not resume prompt
    _wait_only_steps = ("waiting_crm_approval", "waiting_slot_notify")
    # Full prompts map for InterviewBooking steps
    _booking_prompts = lambda _m: {
        "waiting_birth_date": _m.BOOKING_START,
        "waiting_phone": _m.BOOKING_PHONE,
        "waiting_experience": _m.BOOKING_EXPERIENCE,
        "waiting_hw_cpu": _m.BOOKING_HW_CPU,
        "waiting_hw_gpu": _m.BOOKING_HW_GPU,
        "waiting_hw_internet": _m.BOOKING_HW_INTERNET,
        "waiting_hw_remind": _m.BOOKING_HW_CANT_NOW,
        "waiting_tg_nick": _m.BOOKING_TG_NICK,
        "waiting_slot_choice": _m.BOOKING_FETCHING_SLOTS,
        "waiting_slot_preferred": _m.BOOKING_FETCHING_SLOTS,
    }

    # If actively in a form step → resume immediately
    _form_prefixes = ("OperatorForm:", "InterviewBooking:", "AgentForm:", "ModelForm:")
    if current and any(current.startswith(p) for p in _form_prefixes):
        # For wait-only states show status banner instead of confusing resume
        if current.startswith("InterviewBooking:") and current.split(":")[-1] in _wait_only_steps:
            banner = await _build_status_banner(message.from_user.id, data, lang)
            if banner:
                text, kb = banner
                await message.answer(text, reply_markup=kb, parse_mode="Markdown")
            return
        await message.answer(m.RESUME_TEXT)
        if current.startswith("OperatorForm:"):
            from bot.handlers.operator_flow import _send_step_prompt
            await _send_step_prompt(message, state)
        elif current.startswith("ModelForm:"):
            from bot.handlers.model_flow import _send_step_prompt as _model_prompt
            await _model_prompt(message, state)
        elif current.startswith("InterviewBooking:"):
            step = current.split(":")[-1]
            await message.answer(_booking_prompts(m).get(step, m.RESUME_FALLBACK))
        else:
            await message.answer(m.RESUME_FALLBACK)
        return

    # Not in active form → check for paused_state (set when /start or /menu was called mid-form)
    paused = data.get("paused_state")
    if paused and any(paused.startswith(p) for p in _form_prefixes):
        # Wait-only paused states → show status
        if paused.startswith("InterviewBooking:") and paused.split(":")[-1] in _wait_only_steps:
            banner = await _build_status_banner(message.from_user.id, data, lang)
            if banner:
                text, kb = banner
                await message.answer(text, reply_markup=kb, parse_mode="Markdown")
            return
        await state.update_data(paused_state=None)
        await state.set_state(paused)
        await message.answer(m.RESUME_TEXT)
        if paused.startswith("OperatorForm:"):
            from bot.handlers.operator_flow import _send_step_prompt
            await _send_step_prompt(message, state)
        elif paused.startswith("ModelForm:"):
            from bot.handlers.model_flow import _send_step_prompt as _model_prompt
            await _model_prompt(message, state)
        elif paused.startswith("InterviewBooking:"):
            step = paused.split(":")[-1]
            await message.answer(_booking_prompts(m).get(step, m.RESUME_FALLBACK))
        else:
            await message.answer(m.RESUME_FALLBACK)
        return

    # No active form → show status banner from DB or prompt to apply
    banner = await _build_status_banner(message.from_user.id, data, lang)
    if banner:
        text, kb = banner
        await message.answer(text, reply_markup=kb, parse_mode="Markdown")
    else:
        await message.answer(m.CONTINUE_NO_FORM, reply_markup=_main_menu_kb(lang))
        await state.set_state(MenuStates.main_menu)


# --- /ask — pause flow and ask a question (works from any state) ---

@router.message(Command("ask"))
async def cmd_ask(message: Message, state: FSMContext):
    """Pause current flow, let candidate ask a question via /ask menu command."""
    data = await state.get_data()
    lang = _get_lang(data)
    m = msg(lang)
    current = await state.get_state()
    # Save current state so we can resume later
    if current and current != MenuStates.waiting_question.state:
        await state.update_data(paused_state=current)

    resume_kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=m.BTN_CONTINUE, callback_data="resume_form")],
        [InlineKeyboardButton(text=m.BTN_BACK_MENU, callback_data="back_main")],
    ])
    await state.set_state(MenuStates.waiting_question)
    await message.answer(m.ASK_QUESTION_PROMPT_RESUME, reply_markup=resume_kb)


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
    lang = _get_lang(data)
    m = msg(lang)
    has_form = data.get("paused_state") is not None

    if has_form:
        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text=m.BTN_CONTINUE, callback_data="resume_form")],
            [InlineKeyboardButton(text=m.BTN_BACK_MENU, callback_data="back_main")],
        ])
    else:
        kb = _back_kb(lang)

    try:
        await callback.message.edit_text(m.ASK_QUESTION_PROMPT, reply_markup=kb)
    except Exception:
        await callback.message.answer(m.ASK_QUESTION_PROMPT, reply_markup=kb)
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
    lang = _get_lang(data)
    m = msg(lang)
    if data.get("paused_state"):
        # They were in a form — offer to resume
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text=m.BTN_CONTINUE, callback_data="resume_form")],
            [InlineKeyboardButton(text=m.BTN_ASK_ANOTHER, callback_data="menu_question")],
        ])
        await message.answer(m.QUESTION_SENT_RESUME, reply_markup=keyboard)
    else:
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text=m.BTN_ASK_ANOTHER, callback_data="menu_question")],
            [InlineKeyboardButton(text=m.BTN_APPLY, callback_data="menu_apply")],
            [InlineKeyboardButton(text=m.BTN_BACK_MENU, callback_data="back_main")],
        ])
        await message.answer(m.QUESTION_SENT, reply_markup=keyboard)
    await state.set_state(MenuStates.main_menu)


# --- Resume form from /ask or reminder ---

@router.callback_query(F.data == "resume_form")
async def cb_resume_form(callback: CallbackQuery, state: FSMContext):
    """Resume the paused form flow."""
    await callback.answer()
    data = await state.get_data()
    lang = _get_lang(data)
    m = msg(lang)
    paused = data.get("paused_state")

    if not paused:
        # No saved state — go to main menu
        await state.clear()
        await state.update_data(language=lang)
        try:
            await callback.message.edit_text(m.MAIN_MENU_TEXT, reply_markup=_main_menu_kb(lang))
        except Exception:
            await callback.message.answer(m.MAIN_MENU_TEXT, reply_markup=_main_menu_kb(lang))
        await state.set_state(MenuStates.main_menu)
        return

    # Restore the saved state
    await state.update_data(paused_state=None)
    await state.set_state(paused)

    try:
        await callback.message.edit_text(m.RESUME_TEXT)
    except Exception:
        pass

    if paused.startswith("OperatorForm:"):
        from bot.handlers.operator_flow import _send_step_prompt
        await _send_step_prompt(callback, state)
    elif paused.startswith("ModelForm:"):
        from bot.handlers.model_flow import _send_step_prompt as _model_send_step_prompt
        await _model_send_step_prompt(callback, state)
    elif paused.startswith("InterviewBooking:"):
        step = paused.split(":")[-1]
        booking_prompts = {
            "waiting_birth_date": m.BOOKING_START,
            "waiting_phone": m.BOOKING_PHONE,
            "waiting_experience": m.BOOKING_EXPERIENCE,
            "waiting_hw_cpu": m.BOOKING_HW_CPU,
            "waiting_hw_gpu": m.BOOKING_HW_GPU,
            "waiting_hw_internet": m.BOOKING_HW_INTERNET,
            "waiting_hw_remind": m.BOOKING_HW_CANT_NOW,
            "waiting_tg_nick": m.BOOKING_TG_NICK,
            "waiting_slot_choice": m.BOOKING_FETCHING_SLOTS,
            "waiting_slot_preferred": m.BOOKING_FETCHING_SLOTS,
        }
        prompt = booking_prompts.get(step, m.RESUME_FALLBACK)
        await callback.message.answer(prompt)
    else:
        await callback.message.answer(m.RESUME_FALLBACK)


# --- Reminder callbacks (from reminder.py background task) ---

@router.callback_query(F.data.startswith("remind_"))
async def on_reminder_choice(callback: CallbackQuery, state: FSMContext):
    """Handle reminder time choice or 'Continue filling' from reminder prompt."""
    await callback.answer()
    data = await state.get_data()
    lang = _get_lang(data)
    m = msg(lang)
    choice = callback.data.removeprefix("remind_")

    if choice == "continue":
        # Resume current step
        current = await state.get_state()
        await state.update_data(
            reminder_prompt_sent_at=None,
            reminder_scheduled_at=None,
        )
        try:
            await callback.message.edit_text(m.RESUME_TEXT)
        except Exception:
            pass
        if current and current.startswith("OperatorForm:"):
            from bot.handlers.operator_flow import _send_step_prompt
            await _send_step_prompt(callback, state)
        elif current and current.startswith("InterviewBooking:"):
            step = current.split(":")[-1]
            prompts = {
                "waiting_birth_date": m.BOOKING_START,
                "waiting_phone": m.BOOKING_PHONE,
                "waiting_experience": m.BOOKING_EXPERIENCE,
            }
            prompt = prompts.get(step, m.RESUME_FALLBACK)
            await callback.message.answer(prompt)
        else:
            await callback.message.answer(m.RESUME_FALLBACK)
        return

    # Time choice: remind_30, remind_60, remind_180, remind_720
    try:
        minutes = int(choice)
    except ValueError:
        return

    remind_at = datetime.utcnow() + timedelta(minutes=minutes)
    await state.update_data(reminder_scheduled_at=remind_at.isoformat())

    label = m.REMINDER_LABELS.get(minutes, f"{minutes} min")

    try:
        await callback.message.edit_text(m.REMINDER_SET.format(label=label))
    except Exception:
        pass


# --- Apply Now → check duplicate → operator flow ---

@router.callback_query(MenuStates.main_menu, F.data == "menu_apply")
async def cb_menu_apply(callback: CallbackQuery, state: FSMContext):
    await callback.answer()
    data = await state.get_data()
    lang = _get_lang(data)
    m = msg(lang)
    user_id = callback.from_user.id

    # Check if candidate already applied
    try:
        async with async_session() as session:
            result = await session.execute(
                select(Candidate).where(Candidate.tg_user_id == user_id)
            )
            existing = result.scalar_one_or_none()

        if existing:
            status_text = m.STATUS_LABELS.get(existing.status, existing.status)
            keyboard = InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text=m.BTN_REAPPLY, callback_data="reapply")],
                [InlineKeyboardButton(text=m.BTN_BACK_MENU, callback_data="back_main")],
            ])
            dup_text = m.DUPLICATE_CHECK.format(
                name=existing.name.split()[0], status=status_text,
            )
            try:
                await callback.message.edit_text(dup_text, reply_markup=keyboard)
            except Exception:
                await callback.message.answer(dup_text, reply_markup=keyboard)
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
    data = await state.get_data()
    lang = _get_lang(data)
    m = msg(lang)
    await state.update_data(candidate_type="operator")
    fallback_name = "друг" if lang == "ru" else "there"
    greeting = m.WARM_GREETING.format(name=callback.from_user.first_name or fallback_name)
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
    data = await state.get_data()
    lang = _get_lang(data)
    m = msg(lang)
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=m.BTN_APPLY, callback_data="apply_from_info")],
        [InlineKeyboardButton(text=m.BTN_BACK_MENU, callback_data="back_main")],
    ])
    try:
        await callback.message.edit_text(m.VACANCY_TEXT, reply_markup=keyboard)
    except Exception:
        await callback.message.answer(m.VACANCY_TEXT, reply_markup=keyboard)


# --- About the Company ---

@router.callback_query(MenuStates.main_menu, F.data == "menu_company")
async def cb_menu_company(callback: CallbackQuery, state: FSMContext):
    await callback.answer()
    data = await state.get_data()
    lang = _get_lang(data)
    m = msg(lang)
    try:
        await callback.message.edit_text(m.COMPANY_TEXT, reply_markup=_back_kb(lang))
    except Exception:
        await callback.message.answer(m.COMPANY_TEXT, reply_markup=_back_kb(lang))


# --- Catch-all: forward free text in main_menu to admin (enables continuous chat) ---

@router.message(MenuStates.main_menu, F.text)
async def forward_text_to_admin(message: Message, state: FSMContext):
    """Any text typed in main menu → forwarded to admin as a message."""
    text = message.text.strip() if message.text else ""
    if not text or text.startswith("/"):
        return

    data = await state.get_data()
    lang = _get_lang(data)
    m = msg(lang)

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
        await message.answer(m.ERROR_GENERIC)
        return

    await message.answer(
        m.MSG_SENT,
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text=m.BTN_APPLY, callback_data="menu_apply")],
            [InlineKeyboardButton(text=m.BTN_BACK_MENU, callback_data="back_main")],
        ]),
    )
