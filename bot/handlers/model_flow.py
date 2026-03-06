"""10-step FSM flow for Live Stream Entertainer (Model) qualification.

Triggered from menu.py when user selects Model deep link (model_*).
Steps: name -> age -> country/city -> photo -> device -> phone_model ->
       internet -> experience -> availability -> phone

Features:
- Objection auto-handling at every step
- Back button on every step
- Photo collection (selfie)
- Candidate saved to DB at the end
- AI screening via Groq
- PASS -> interview booking, REJECT -> agent offer, MAYBE -> admin review
- Notion lead sync
"""

from __future__ import annotations

import json
import logging

from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup, Message
from sqlalchemy import select

from bot.config import config
from bot.database import async_session
from bot.database.models import Candidate, FunnelEvent
from bot.messages import msg
from bot.services.objection_handler import detect_objection, get_response
from bot.services import notion_leads
from bot.services.claude_client import claude as ai_client
from bot.services.huntme_crm import parse_phone

logger = logging.getLogger(__name__)
router = Router()


# ═══ HELPERS ═══

async def _track_event(tg_user_id: int, event_type: str, step_name: str = None, data: dict = None):
    """Record a funnel event to the database."""
    try:
        async with async_session() as session:
            event = FunnelEvent(
                tg_user_id=tg_user_id,
                event_type=event_type,
                step_name=step_name,
                data=json.dumps(data, ensure_ascii=False) if data else None,
            )
            session.add(event)
            await session.commit()
    except Exception:
        logger.debug("Failed to track funnel event", exc_info=True)


def _back_row(lang: str = "en"):
    """Single back button row to append to any keyboard."""
    return [InlineKeyboardButton(text=msg(lang).BTN_BACK, callback_data="model_go_back")]


def _progress(step: int, total: int = 10) -> str:
    """Minimal step counter."""
    return f"Step {step}/{total}"


# ═══ FSM STATES ═══

class ModelForm(StatesGroup):
    waiting_name = State()
    waiting_age = State()
    waiting_country = State()
    waiting_photo = State()
    waiting_device = State()
    waiting_phone_model = State()
    waiting_internet = State()
    waiting_experience = State()
    waiting_availability = State()
    waiting_phone = State()


# Step order for back navigation
STEP_BACK = {
    ModelForm.waiting_name.state: None,
    ModelForm.waiting_age.state: ModelForm.waiting_name.state,
    ModelForm.waiting_country.state: ModelForm.waiting_age.state,
    ModelForm.waiting_photo.state: ModelForm.waiting_country.state,
    ModelForm.waiting_device.state: ModelForm.waiting_photo.state,
    ModelForm.waiting_phone_model.state: ModelForm.waiting_device.state,
    ModelForm.waiting_internet.state: ModelForm.waiting_phone_model.state,
    ModelForm.waiting_experience.state: ModelForm.waiting_internet.state,
    ModelForm.waiting_availability.state: ModelForm.waiting_experience.state,
    ModelForm.waiting_phone.state: ModelForm.waiting_availability.state,
}


# ═══ QUESTION / OBJECTION HANDLING ═══

async def _handle_possible_question(message: Message, state: FSMContext) -> bool:
    """Check if message is a question/objection. Handle it and return True, or return False."""
    text = message.text.strip() if message.text else ""
    if not text:
        return False

    data = await state.get_data()
    lang = data.get("language", "en")

    has_question_mark = "?" in text
    is_conversational = len(text) > 40

    if has_question_mark or is_conversational:
        objection = detect_objection(text, lang)
        if objection:
            response = get_response(objection, lang)
            if response:
                current = await state.get_state()
                await _track_event(message.from_user.id, "objection_detected", current, {"objection": objection, "text": text[:200]})
                await message.answer(response)
                await _send_step_prompt(message, state)
                return True

    if has_question_mark:
        current = await state.get_state()
        await _track_event(message.from_user.id, "question_asked", current, {"text": text[:200]})
        await _forward_question_to_admin(message, state, text)
        return True

    return False


async def _forward_question_to_admin(message: Message, state: FSMContext, text: str):
    """Forward candidate's question to admin for manual reply."""
    data = await state.get_data()
    lang = data.get("language", "en")
    m = msg(lang)
    current = await state.get_state()
    name = data.get("name", "Unknown")
    username = message.from_user.username or "N/A"

    admin_text = (
        f"[MODEL] Question from {name} "
        f"(@{username}, ID: {message.from_user.id})\n"
        f"Step: {current}\n\n"
        f"{text}\n\n"
        f"Reply to this message to answer the candidate."
    )
    try:
        await message.bot.send_message(config.ADMIN_CHAT_ID, admin_text)
    except Exception:
        logger.exception("Failed to forward question to admin")

    await message.answer(m.QUESTION_FORWARDED)
    await _send_step_prompt(message, state)


# ═══ STEP PROMPT SENDER (used for back nav + question reminders) ═══

async def _send_step_prompt(target, state: FSMContext, set_state=False):
    """Send the prompt for the current state. target: Message or CallbackQuery."""
    current = await state.get_state()
    data = await state.get_data()
    lang = data.get("language", "en")
    m = msg(lang)
    send = target.message.answer if isinstance(target, CallbackQuery) else target.answer

    if current == ModelForm.waiting_name.state:
        kb = InlineKeyboardMarkup(inline_keyboard=[_back_row(lang)])
        await send(f"{_progress(1)}\n\n{m.MODEL_STEP_NAME}", reply_markup=kb)

    elif current == ModelForm.waiting_age.state:
        kb = InlineKeyboardMarkup(inline_keyboard=[_back_row(lang)])
        await send(f"{_progress(2)}\n\n{m.MODEL_STEP_AGE}", reply_markup=kb)

    elif current == ModelForm.waiting_country.state:
        kb = InlineKeyboardMarkup(inline_keyboard=[_back_row(lang)])
        await send(f"{_progress(3)}\n\n{m.MODEL_STEP_COUNTRY}", reply_markup=kb)

    elif current == ModelForm.waiting_photo.state:
        kb = InlineKeyboardMarkup(inline_keyboard=[_back_row(lang)])
        await send(f"{_progress(4)}\n\n{m.MODEL_STEP_PHOTO}", reply_markup=kb)

    elif current == ModelForm.waiting_device.state:
        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text=m.BTN_MODEL_PHONE_ONLY, callback_data="mdev_phone")],
            [InlineKeyboardButton(text=m.BTN_MODEL_LAPTOP, callback_data="mdev_laptop")],
            [InlineKeyboardButton(text=m.BTN_MODEL_BOTH, callback_data="mdev_both")],
            _back_row(lang),
        ])
        await send(f"{_progress(5)}\n\n{m.MODEL_STEP_DEVICE}", reply_markup=kb)

    elif current == ModelForm.waiting_phone_model.state:
        kb = InlineKeyboardMarkup(inline_keyboard=[_back_row(lang)])
        await send(f"{_progress(6)}\n\n{m.MODEL_STEP_DEVICE_PHONE_MODEL}", reply_markup=kb)

    elif current == ModelForm.waiting_internet.state:
        kb = InlineKeyboardMarkup(inline_keyboard=[_back_row(lang)])
        await send(f"{_progress(7)}\n\n{m.MODEL_STEP_INTERNET}", reply_markup=kb)

    elif current == ModelForm.waiting_experience.state:
        kb = InlineKeyboardMarkup(inline_keyboard=[_back_row(lang)])
        await send(f"{_progress(8)}\n\n{m.MODEL_STEP_EXPERIENCE}", reply_markup=kb)

    elif current == ModelForm.waiting_availability.state:
        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text=m.BTN_MODEL_SCHED_MORNING, callback_data="mavail_morning")],
            [InlineKeyboardButton(text=m.BTN_MODEL_SCHED_DAY, callback_data="mavail_day")],
            [InlineKeyboardButton(text=m.BTN_MODEL_SCHED_EVENING, callback_data="mavail_evening")],
            [InlineKeyboardButton(text=m.BTN_MODEL_SCHED_NIGHT, callback_data="mavail_night")],
            [InlineKeyboardButton(text=m.BTN_MODEL_SCHED_FLEXIBLE, callback_data="mavail_flexible")],
            _back_row(lang),
        ])
        await send(f"{_progress(9)}\n\n{m.MODEL_STEP_AVAILABILITY}", reply_markup=kb)

    elif current == ModelForm.waiting_phone.state:
        kb = InlineKeyboardMarkup(inline_keyboard=[_back_row(lang)])
        await send(f"{_progress(10)}\n\n{m.MODEL_STEP_PHONE}", reply_markup=kb)


# ═══ BACK NAVIGATION ═══

@router.callback_query(F.data == "model_go_back")
async def on_back(callback: CallbackQuery, state: FSMContext):
    """Navigate to previous step or main menu."""
    await callback.answer()
    current = await state.get_state()

    prev = STEP_BACK.get(current) if current else None
    if prev is None:
        # Go to main menu
        data = await state.get_data()
        lang = data.get("language", "en")
        m = msg(lang)
        await state.clear()
        await state.update_data(language=lang)
        from bot.handlers.menu import MenuStates, _main_menu_kb
        try:
            await callback.message.edit_text(m.MAIN_MENU_TEXT, reply_markup=_main_menu_kb(lang))
        except Exception:
            await callback.message.answer(m.MAIN_MENU_TEXT, reply_markup=_main_menu_kb(lang))
        await state.set_state(MenuStates.main_menu)
        return

    await state.set_state(prev)
    await _send_step_prompt(callback, state)


# ═══ STEP 1: Name ═══

@router.message(ModelForm.waiting_name)
async def process_name(message: Message, state: FSMContext):
    if await _handle_possible_question(message, state):
        return

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
    await _track_event(message.from_user.id, "step_completed", "model_name", {"name": name})

    # Notion sync
    notion_page_id = data.get("notion_page_id")
    if notion_page_id:
        await notion_leads.on_name(notion_page_id, name)

    await state.set_state(ModelForm.waiting_age)
    await _send_step_prompt(message, state)


# ═══ STEP 2: Age ═══

@router.message(ModelForm.waiting_age)
async def process_age(message: Message, state: FSMContext):
    if await _handle_possible_question(message, state):
        return

    text = (message.text or "").strip()
    data = await state.get_data()
    lang = data.get("language", "en")
    m = msg(lang)

    age = None
    for word in text.split():
        if word.isdigit():
            age = int(word)
            break
    if age is None:
        try:
            age = int(text)
        except ValueError:
            await message.answer(m.MODEL_STEP_AGE_VALIDATION)
            return

    if age < 18:
        await message.answer(m.DECLINE_UNDERAGE)
        await _track_event(message.from_user.id, "declined", "model_age", {"age": age, "reason": "underage"})
        await state.clear()
        return

    await state.update_data(age=age)
    await _track_event(message.from_user.id, "step_completed", "model_age", {"age": age})

    # Notion sync
    notion_page_id = data.get("notion_page_id")
    if notion_page_id:
        await notion_leads.on_age(notion_page_id, age)

    await state.set_state(ModelForm.waiting_country)
    await _send_step_prompt(message, state)


# ═══ STEP 3: Country/City ═══

@router.message(ModelForm.waiting_country)
async def process_country(message: Message, state: FSMContext):
    if await _handle_possible_question(message, state):
        return

    text = (message.text or "").strip()
    data = await state.get_data()
    lang = data.get("language", "en")

    if len(text) < 2:
        m = msg(lang)
        await message.answer(m.MODEL_STEP_COUNTRY)
        return

    await state.update_data(country_city=text)
    await _track_event(message.from_user.id, "step_completed", "model_country", {"country_city": text})

    await state.set_state(ModelForm.waiting_photo)
    await _send_step_prompt(message, state)


# ═══ STEP 4: Photo (selfie) ═══

@router.message(ModelForm.waiting_photo)
async def process_photo(message: Message, state: FSMContext):
    data = await state.get_data()
    lang = data.get("language", "en")
    m = msg(lang)

    if not message.photo:
        # Check if text — might be a question
        if message.text and await _handle_possible_question(message, state):
            return
        await message.answer(m.MODEL_STEP_PHOTO_VALIDATION)
        return

    # Save photo file_id (highest resolution)
    photo = message.photo[-1]
    await state.update_data(
        photo_file_id=photo.file_id,
        photo_status="selfie_received",
    )
    await message.answer(m.MODEL_STEP_PHOTO_RECEIVED)
    await _track_event(message.from_user.id, "step_completed", "model_photo", {"file_id": photo.file_id})

    await state.set_state(ModelForm.waiting_device)
    await _send_step_prompt(message, state)


# ═══ STEP 5: Device ═══

@router.callback_query(ModelForm.waiting_device, F.data.startswith("mdev_"))
async def process_device(callback: CallbackQuery, state: FSMContext):
    device = callback.data.removeprefix("mdev_")
    await callback.answer()

    device_map = {
        "phone": "Smartphone only",
        "laptop": "Laptop/PC with camera",
        "both": "Both smartphone and laptop/PC",
    }
    await state.update_data(device_type=device_map.get(device, device))
    await _track_event(callback.from_user.id, "step_completed", "model_device", {"device": device})

    await state.set_state(ModelForm.waiting_phone_model)
    await _send_step_prompt(callback, state)


# ═══ STEP 6: Phone model ═══

@router.message(ModelForm.waiting_phone_model)
async def process_phone_model(message: Message, state: FSMContext):
    if await _handle_possible_question(message, state):
        return

    text = (message.text or "").strip()
    data = await state.get_data()
    lang = data.get("language", "en")
    m = msg(lang)

    if len(text) < 2:
        await message.answer(m.MODEL_STEP_DEVICE_PHONE_MODEL)
        return

    await state.update_data(phone_model_device=text)
    await _track_event(message.from_user.id, "step_completed", "model_phone_model", {"value": text})

    # Social proof after halfway
    await message.answer(m.MODEL_SOCIAL_PROOF)

    await state.set_state(ModelForm.waiting_internet)
    await _send_step_prompt(message, state)


# ═══ STEP 7: Internet ═══

@router.message(ModelForm.waiting_internet)
async def process_internet(message: Message, state: FSMContext):
    if await _handle_possible_question(message, state):
        return

    text = (message.text or "").strip()
    data = await state.get_data()
    lang = data.get("language", "en")

    if len(text) < 2:
        m = msg(lang)
        await message.answer(m.MODEL_STEP_INTERNET)
        return

    await state.update_data(internet_speed=text)
    await _track_event(message.from_user.id, "step_completed", "model_internet", {"value": text})

    await state.set_state(ModelForm.waiting_experience)
    await _send_step_prompt(message, state)


# ═══ STEP 8: Experience ═══

@router.message(ModelForm.waiting_experience)
async def process_experience(message: Message, state: FSMContext):
    if await _handle_possible_question(message, state):
        return

    text = (message.text or "").strip()
    data = await state.get_data()
    lang = data.get("language", "en")

    if len(text) < 2:
        m = msg(lang)
        await message.answer(m.MODEL_STEP_EXPERIENCE)
        return

    await state.update_data(platform_experience=text)
    await _track_event(message.from_user.id, "step_completed", "model_experience", {"value": text})

    await state.set_state(ModelForm.waiting_availability)
    await _send_step_prompt(message, state)


# ═══ STEP 9: Availability ═══

@router.callback_query(ModelForm.waiting_availability, F.data.startswith("mavail_"))
async def process_availability(callback: CallbackQuery, state: FSMContext):
    choice = callback.data.removeprefix("mavail_")
    await callback.answer()

    sched_map = {
        "morning": "Morning (6:00-12:00)",
        "day": "Day (12:00-18:00)",
        "evening": "Evening (18:00-00:00)",
        "night": "Night (00:00-6:00)",
        "flexible": "Flexible / Multiple shifts",
    }
    await state.update_data(preferred_schedule=sched_map.get(choice, choice))
    await _track_event(callback.from_user.id, "step_completed", "model_availability", {"value": choice})

    await state.set_state(ModelForm.waiting_phone)
    await _send_step_prompt(callback, state)


# ═══ STEP 10: Phone -> Screening ═══

@router.message(ModelForm.waiting_phone)
async def process_phone(message: Message, state: FSMContext):
    data_pre = await state.get_data()
    lang = data_pre.get("language", "en")
    m = msg(lang)

    if not message.text:
        await message.answer(m.PHONE_VALIDATION)
        return

    if await _handle_possible_question(message, state):
        return

    raw = message.text.strip()
    digits, country = parse_phone(raw)

    if len(digits) < 7:
        await message.answer(m.PHONE_VALIDATION)
        return

    await state.update_data(
        phone_number=digits,
        phone_country=country,
        contact_info=raw,
    )
    await _track_event(message.from_user.id, "step_completed", "model_phone", {"value": digits})
    data = await state.get_data()

    # Prevent duplicate processing: clear state before screening
    await state.set_state(None)

    # AI screening
    await message.answer(m.MODEL_APPLICATION_COMPLETE)

    import asyncio
    await asyncio.sleep(5)

    result = await _screen_model(data, message.from_user.username, lang)

    await _track_event(message.from_user.id, "completed", "model_screening", {
        "score": result["overall_score"],
        "recommendation": result["recommendation"],
    })

    await _save_candidate(
        message, data,
        status="screened",
        score=result["overall_score"],
        recommendation=result["recommendation"],
        notes=result["reasoning"],
    )

    await notion_leads.on_complete(
        page_id=data.get("notion_page_id"),
        tg_id=message.from_user.id,
        tg_username=message.from_user.username,
        data=data,
        recommendation=result["recommendation"],
        score=result["overall_score"],
        notes=result["reasoning"],
    )

    # PASS -> auto-start interview booking
    # MAYBE -> send clarifying question, admin will decide
    # REJECT -> decline + agent offer
    if result["recommendation"] == "PASS":
        await state.update_data(ai_score=result["overall_score"], ai_recommendation="PASS")
        from bot.handlers.interview_booking import start_booking
        await start_booking(message, state, message.from_user.id)
    elif result["recommendation"] == "MAYBE":
        await state.set_state(None)
        await message.answer(result["suggested_response"])
    else:
        # REJECT -> offer agent role
        await state.set_state(None)
        from bot.handlers.agent_flow import send_agent_offer
        await send_agent_offer(message.bot, message.chat.id, result["suggested_response"], lang)

    await _notify_admin_model(message, data, result)


# ═══ AI SCREENING ═══

async def _screen_model(data: dict, tg_username: str, language: str) -> dict:
    """Screen model candidate via AI. Returns dict with scores + recommendation."""
    m = msg(language)

    prompt = m.MODEL_SCREENER_TEMPLATE.format(
        name=data.get("name", "N/A"),
        age=data.get("age", "N/A"),
        country_city=data.get("country_city", "N/A"),
        photo_status=data.get("photo_status", "no photo"),
        device_type=data.get("device_type", "N/A"),
        phone_model=data.get("phone_model_device", "N/A"),
        internet=data.get("internet_speed", "N/A"),
        experience=data.get("platform_experience", "N/A"),
        availability=data.get("preferred_schedule", "N/A"),
        phone=data.get("contact_info", "N/A"),
        tg_username=tg_username or "N/A",
    )

    system = m.MODEL_SCREENER_SYSTEM + "\n\n" + m.SCREENER_RESPONSE_LANG

    try:
        raw = await ai_client.complete(
            system=system,
            user_message=prompt,
            max_tokens=600,
        )

        # Strip markdown fences
        cleaned = raw.strip()
        if cleaned.startswith("```"):
            cleaned = cleaned.split("\n", 1)[1]
        if cleaned.endswith("```"):
            cleaned = cleaned.rsplit("```", 1)[0]
        cleaned = cleaned.strip()

        result = json.loads(cleaned)
        # Ensure required keys exist
        result.setdefault("overall_score", 0)
        result.setdefault("recommendation", "MAYBE")
        result.setdefault("reasoning", "")
        result.setdefault("suggested_response", "")
        return result

    except Exception:
        logger.exception("Model AI screening failed - using fallback")
        m_lang = msg(language)
        return {
            "appearance_score": 0,
            "device_score": 0,
            "internet_score": 0,
            "availability_score": 0,
            "experience_score": 0,
            "motivation_score": 0,
            "overall_score": 0,
            "recommendation": "MAYBE",
            "reasoning": "AI screening unavailable - manual review needed",
            "suggested_response": m_lang.MODEL_APPLICATION_FALLBACK,
        }


# ═══ DB SAVE ═══

async def _save_candidate(message, data, status="new", score=None, recommendation=None, notes=None):
    """Save or update model candidate in the database."""
    from_user = message.from_user
    try:
        async with async_session() as session:
            result = await session.execute(
                select(Candidate).where(Candidate.tg_user_id == from_user.id)
            )
            candidate = result.scalar_one_or_none()

            lang = data.get("language", "en")
            region = data.get("country_city", "").split(",")[0].strip() if data.get("country_city") else None

            fields = dict(
                tg_username=from_user.username,
                name=data.get("name", "Unknown"),
                candidate_type="model",
                language=lang,
                region=region,
                age=data.get("age"),
                contact_info=data.get("contact_info"),
                phone_number=data.get("phone_number"),
                phone_country=data.get("phone_country"),
                platform_experience=data.get("platform_experience"),
                preferred_schedule=data.get("preferred_schedule"),
                internet_speed=data.get("internet_speed"),
                score=score,
                recommendation=recommendation,
                status=status,
                notes=notes,
            )

            if candidate:
                for k, v in fields.items():
                    setattr(candidate, k, v)
            else:
                candidate = Candidate(
                    tg_user_id=from_user.id,
                    referrer_tg_id=data.get("referrer_tg_id"),
                    utm_source=data.get("utm_source"),
                    **fields,
                )
                session.add(candidate)

            await session.commit()
            logger.info("Saved model candidate %s (tg_id=%s, status=%s)", data.get("name"), from_user.id, status)
    except Exception:
        logger.exception("Failed to save model candidate to DB")


# ═══ ADMIN NOTIFICATION ═══

async def _notify_admin_model(message, data, result):
    """Send model application summary to admin chat."""
    icon = {"PASS": "PASS", "MAYBE": "MAYBE", "REJECT": "REJECT"}.get(result["recommendation"], "?")
    emoji = {"PASS": "🟢", "MAYBE": "🟡", "REJECT": "🔴"}.get(result["recommendation"], "❓")

    photo_info = "Selfie received" if data.get("photo_file_id") else "No photo"

    admin_text = (
        f"[MODEL] {emoji} {icon} - Score: {result['overall_score']}/100\n\n"
        f"Name: {data.get('name', 'N/A')}\n"
        f"TG: @{message.from_user.username or 'N/A'} (ID: {message.from_user.id})\n"
        f"Age: {data.get('age', 'N/A')}\n"
        f"Country/City: {data.get('country_city', 'N/A')}\n"
        f"Photo: {photo_info}\n"
        f"Device: {data.get('device_type', 'N/A')} ({data.get('phone_model_device', 'N/A')})\n"
        f"Internet: {data.get('internet_speed', 'N/A')}\n"
        f"Experience: {data.get('platform_experience', 'N/A')}\n"
        f"Schedule: {data.get('preferred_schedule', 'N/A')}\n"
        f"Phone: {data.get('phone_number', 'N/A')} ({data.get('phone_country', 'N/A')})\n"
        f"{'Source: ' + data.get('utm_source', '') + chr(10) if data.get('utm_source') else ''}"
        f"Lang: {data.get('language', 'en').upper()}\n\n"
        f"Reasoning: {result.get('reasoning', 'N/A')}"
    )

    # PASS: booking auto-started, no Interview button needed
    # MAYBE/REJECT: admin can manually invite or reject
    if result["recommendation"] == "PASS":
        buttons = [
            [
                InlineKeyboardButton(text="❌ Reject", callback_data=f"rej_{message.from_user.id}"),
                InlineKeyboardButton(text="💬 Message", callback_data=f"msg_{message.from_user.id}"),
            ],
        ]
    else:
        buttons = [
            [
                InlineKeyboardButton(text="✅ Interview", callback_data=f"ref_{message.from_user.id}"),
                InlineKeyboardButton(text="❌ Reject", callback_data=f"rej_{message.from_user.id}"),
            ],
            [
                InlineKeyboardButton(text="💬 Message", callback_data=f"msg_{message.from_user.id}"),
            ],
        ]
    keyboard = InlineKeyboardMarkup(inline_keyboard=buttons)

    try:
        await message.bot.send_message(config.ADMIN_CHAT_ID, admin_text, reply_markup=keyboard)
    except Exception:
        logger.exception("Failed to notify admin about model application")

    # Forward selfie to admin if available
    photo_file_id = data.get("photo_file_id")
    if photo_file_id:
        try:
            await message.bot.send_photo(
                config.ADMIN_CHAT_ID,
                photo_file_id,
                caption=f"Selfie from {data.get('name', 'N/A')} (@{message.from_user.username or 'N/A'})",
            )
        except Exception:
            logger.debug("Failed to send selfie to admin")


# ═══ AGENT REDIRECT ═══
# The "become_agent" callback is handled in operator_flow.py (no state filter,
# catches all clicks). Model flow uses the same send_agent_offer() function
# from agent_flow.py, which generates the same "become_agent" button.
# No duplicate handler needed here.
