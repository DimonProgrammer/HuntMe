"""11-step FSM flow for operator (Live Stream Moderator) qualification.

Steps: name → PC → age → study/work → english → PC confidence →
       CPU → GPU → internet → start date → contact

Features:
- Objection auto-handling at every step
- Unknown questions forwarded to admin (admin replies via bot)
- Back button on every step
- Candidate saved to DB at the end
- AI screening via OpenRouter / fallback
"""

from __future__ import annotations

import base64
import io
import json
import logging

import aiohttp
from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup, Message

from bot.config import config
from bot.database import async_session
from bot.database.models import Candidate, FunnelEvent
from bot.services.hardware_checker import quick_check
from bot.services.objection_handler import detect_objection, get_response
from bot.services.screener import ScreeningResult, screen_candidate
from bot.services import notion_leads
from bot.services.claude_client import claude as ai_client

logger = logging.getLogger(__name__)
router = Router()


async def _extract_from_photo(message: Message, prompt: str) -> str | None:
    """Download photo from Telegram, send to vision AI, return extracted text or None."""
    try:
        photo = message.photo[-1]  # highest resolution
        file = await message.bot.get_file(photo.file_id)
        buf = io.BytesIO()
        await message.bot.download_file(file.file_path, buf)
        image_b64 = base64.b64encode(buf.getvalue()).decode("utf-8")
        result = await ai_client.vision_complete(prompt=prompt, image_base64=image_b64)
        return result.strip() if result and result.strip() else None
    except Exception:
        logger.exception("Vision extraction failed")
        return None


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


class OperatorForm(StatesGroup):
    waiting_name = State()
    waiting_has_pc = State()
    waiting_no_pc_followup = State()
    waiting_age = State()
    waiting_study_work = State()
    waiting_english = State()
    waiting_pc_confidence = State()
    waiting_cpu = State()
    waiting_cpu_simple_age = State()      # "Not sure" → how old is PC
    waiting_cpu_simple_usage = State()    # "Not sure" → what's it used for
    waiting_gpu = State()
    waiting_gpu_simple_gaming = State()   # "Not sure" → can it play games
    waiting_internet = State()
    waiting_start_date = State()
    waiting_contact = State()


# Step order for back navigation (state → previous state)
# None means "go back to main menu"
STEP_BACK = {
    OperatorForm.waiting_name.state: None,
    OperatorForm.waiting_has_pc.state: OperatorForm.waiting_name.state,
    OperatorForm.waiting_no_pc_followup.state: OperatorForm.waiting_has_pc.state,
    OperatorForm.waiting_age.state: OperatorForm.waiting_has_pc.state,
    OperatorForm.waiting_study_work.state: OperatorForm.waiting_age.state,
    OperatorForm.waiting_english.state: OperatorForm.waiting_study_work.state,
    OperatorForm.waiting_pc_confidence.state: OperatorForm.waiting_english.state,
    OperatorForm.waiting_cpu.state: OperatorForm.waiting_pc_confidence.state,
    OperatorForm.waiting_cpu_simple_age.state: OperatorForm.waiting_cpu.state,
    OperatorForm.waiting_cpu_simple_usage.state: OperatorForm.waiting_cpu_simple_age.state,
    OperatorForm.waiting_gpu.state: OperatorForm.waiting_cpu.state,
    OperatorForm.waiting_gpu_simple_gaming.state: OperatorForm.waiting_gpu.state,
    OperatorForm.waiting_internet.state: OperatorForm.waiting_gpu.state,
    OperatorForm.waiting_start_date.state: OperatorForm.waiting_internet.state,
    OperatorForm.waiting_contact.state: OperatorForm.waiting_start_date.state,
}


def _back_row():
    """Single back button row to append to any keyboard."""
    return [InlineKeyboardButton(text="⬅️ Back", callback_data="go_back")]


# ═══ QUESTION / OBJECTION HANDLING ═══

async def _handle_possible_question(message: Message, state: FSMContext) -> bool:
    """Check if message is a question/objection. Handle it and return True, or return False."""
    text = message.text.strip() if message.text else ""
    if not text:
        return False

    has_question_mark = "?" in text
    is_conversational = len(text) > 40

    if has_question_mark or is_conversational:
        objection = detect_objection(text)
        if objection:
            response = get_response(objection)
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
    current = await state.get_state()
    name = data.get("name", "Unknown")
    username = message.from_user.username or "N/A"

    admin_text = (
        f"❓ QUESTION from {name} "
        f"(@{username}, ID: {message.from_user.id})\n"
        f"Step: {current}\n\n"
        f"{text}\n\n"
        f"Reply to this message to answer the candidate."
    )
    try:
        await message.bot.send_message(config.ADMIN_CHAT_ID, admin_text)
    except Exception:
        logger.exception("Failed to forward question to admin")

    await message.answer(
        "Great question! I've forwarded it to our team — "
        "they'll get back to you shortly. 🙂\n\n"
        "In the meantime, let's continue with the application."
    )
    await _send_step_prompt(message, state)


# ═══ STEP PROMPT SENDER (used for back nav + question reminders) ═══

def _progress(step: int, total: int = 11) -> str:
    """Minimal step counter."""
    return f"Step {step}/{total}"


async def _send_step_prompt(target, state: FSMContext, set_state=False):
    """Send the prompt for the current state. target: Message or CallbackQuery."""
    current = await state.get_state()
    data = await state.get_data()
    send = target.message.answer if isinstance(target, CallbackQuery) else target.answer

    if current == OperatorForm.waiting_name.state:
        kb = InlineKeyboardMarkup(inline_keyboard=[_back_row()])
        await send(f"{_progress(1)}\n\nWhat is your full name?", reply_markup=kb)

    elif current == OperatorForm.waiting_has_pc.state:
        kb = InlineKeyboardMarkup(inline_keyboard=[
            [
                InlineKeyboardButton(text="🖥️ Yes, PC/Desktop", callback_data="pc_desktop"),
                InlineKeyboardButton(text="💻 Yes, Laptop", callback_data="pc_laptop"),
            ],
            [InlineKeyboardButton(text="❌ No", callback_data="pc_no")],
            _back_row(),
        ])
        await send(
            f"{_progress(2)}\n\n"
            "Do you have a Windows PC or laptop?",
            reply_markup=kb,
        )

    elif current == OperatorForm.waiting_no_pc_followup.state:
        kb = InlineKeyboardMarkup(inline_keyboard=[
            [
                InlineKeyboardButton(text="✅ Yes, within 1-2 weeks", callback_data="nopc_soon"),
                InlineKeyboardButton(text="🤷 No plans yet", callback_data="nopc_no"),
            ],
            _back_row(),
        ])
        await send("Are you planning to get a Windows PC in the near future?", reply_markup=kb)

    elif current == OperatorForm.waiting_age.state:
        kb = InlineKeyboardMarkup(inline_keyboard=[_back_row()])
        await send(f"{_progress(3)}\n\nHow old are you?", reply_markup=kb)

    elif current == OperatorForm.waiting_study_work.state:
        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="💼 Working", callback_data="study_working")],
            [InlineKeyboardButton(text="🎓 Student (online classes)", callback_data="study_distance")],
            [InlineKeyboardButton(text="🏫 Student (on campus)", callback_data="study_inperson")],
            [InlineKeyboardButton(text="🏠 Neither", callback_data="study_neither")],
            _back_row(),
        ])
        await send(f"{_progress(4)}\n\nAre you currently studying or working?", reply_markup=kb)

    elif current == OperatorForm.waiting_english.state:
        kb = InlineKeyboardMarkup(inline_keyboard=[
            [
                InlineKeyboardButton(text="📗 Basic", callback_data="eng_beginner"),
                InlineKeyboardButton(text="📘 Can hold a conversation", callback_data="eng_b1"),
            ],
            [
                InlineKeyboardButton(text="📙 Comfortable", callback_data="eng_b2"),
                InlineKeyboardButton(text="📕 Fluent", callback_data="eng_c1"),
            ],
            [InlineKeyboardButton(text="🌟 Native speaker", callback_data="eng_native")],
            _back_row(),
        ])
        await send(
            f"{_progress(5)}\n\n"
            "How well do you speak English?\n\n"
            "We need at least conversational level — you'll be moderating English chats.\n\n"
            "You can also rate yourself from 1 to 10.",
            reply_markup=kb,
        )

    elif current == OperatorForm.waiting_pc_confidence.state:
        kb = InlineKeyboardMarkup(inline_keyboard=[_back_row()])
        await send(
            f"{_progress(6)}\n\n"
            "How comfortable are you with Windows?\n\n"
            "For example: installing programs, troubleshooting, changing settings?\n\n"
            "You can rate yourself from 1 to 10.",
            reply_markup=kb,
        )

    elif current == OperatorForm.waiting_cpu.state:
        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🤔 Not sure", callback_data="cpu_skip")],
            _back_row(),
        ])
        await send(
            f"{_progress(7)}\n\n"
            "What is your processor (CPU)?\n\n"
            "How to check:\n"
            "Settings > System > About > look for 'Processor'\n\n"
            "Example: Intel Core i5-12400 or AMD Ryzen 5 5600\n\n"
            "Not sure? Tap the button — we'll ask a few simple questions instead.",
            reply_markup=kb,
        )

    elif current == OperatorForm.waiting_cpu_simple_age.state:
        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🆕 Less than 2 years", callback_data="pcage_new")],
            [InlineKeyboardButton(text="📅 2-4 years", callback_data="pcage_mid")],
            [InlineKeyboardButton(text="📆 5+ years", callback_data="pcage_old")],
            [InlineKeyboardButton(text="🤔 Not sure", callback_data="pcage_unsure")],
            _back_row(),
        ])
        await send(
            f"{_progress(7)} — No worries! A few quick questions instead.\n\n"
            "How old is your computer?",
            reply_markup=kb,
        )

    elif current == OperatorForm.waiting_cpu_simple_usage.state:
        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🎮 Gaming", callback_data="pcuse_gaming")],
            [InlineKeyboardButton(text="💼 Work / Office", callback_data="pcuse_work")],
            [InlineKeyboardButton(text="🌐 Browsing / Social media", callback_data="pcuse_browsing")],
            [InlineKeyboardButton(text="🎨 Video editing / Design", callback_data="pcuse_creative")],
            _back_row(),
        ])
        await send(f"{_progress(7)}\n\nWhat do you mainly use your computer for?", reply_markup=kb)

    elif current == OperatorForm.waiting_gpu.state:
        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🤔 Not sure", callback_data="gpu_skip")],
            _back_row(),
        ])
        await send(
            f"{_progress(8)}\n\n"
            "What is your graphics card (GPU)?\n\n"
            "How to check:\n"
            "Settings > System > Display > Advanced display > look for GPU info\n\n"
            "Example: NVIDIA GeForce RTX 3060 or AMD Radeon RX 6600\n\n"
            "Not sure? Tap the button below.",
            reply_markup=kb,
        )

    elif current == OperatorForm.waiting_gpu_simple_gaming.state:
        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🎮 Yes, modern games (GTA, Fortnite)", callback_data="game_modern")],
            [InlineKeyboardButton(text="🕹️ Yes, but only simple/old games", callback_data="game_basic")],
            [InlineKeyboardButton(text="❌ No / Never tried", callback_data="game_no")],
            [InlineKeyboardButton(text="🤔 Not sure", callback_data="game_unsure")],
            _back_row(),
        ])
        await send(
            f"{_progress(8)} — One more quick question.\n\n"
            "Can your computer run video games?",
            reply_markup=kb,
        )

    elif current == OperatorForm.waiting_internet.state:
        kb = InlineKeyboardMarkup(inline_keyboard=[_back_row()])
        await send(
            f"{_progress(9)}\n\n"
            "What is your internet speed?\n\n"
            "You can check at speedtest.net\n\n"
            "Also — are you on WiFi or plugged in with a cable?",
            reply_markup=kb,
        )

    elif current == OperatorForm.waiting_start_date.state:
        kb = InlineKeyboardMarkup(inline_keyboard=[_back_row()])
        await send(
            f"{_progress(10)}\n\n"
            "When would you be ready to start?\n\n"
            "We can schedule your interview and start training the same day!",
            reply_markup=kb,
        )

    elif current == OperatorForm.waiting_contact.state:
        kb = InlineKeyboardMarkup(inline_keyboard=[_back_row()])
        await send(
            f"{_progress(11)} — Last one!\n\n"
            "Please share your contact for the interview:\n"
            "• Telegram @username (preferred)\n• Or WhatsApp number",
            reply_markup=kb,
        )


# ═══ UNIVERSAL BACK HANDLER ═══

@router.callback_query(F.data == "go_back")
async def cb_go_back(callback: CallbackQuery, state: FSMContext):
    """Go back to the previous step."""
    await callback.answer()
    current = await state.get_state()
    data = await state.get_data()
    prev_state = STEP_BACK.get(current)

    # Landing leads skip the name step — go straight to menu
    if prev_state == OperatorForm.waiting_name.state and data.get("utm_source") == "landing":
        prev_state = None

    if prev_state is None:
        # Back to main menu
        from bot.handlers.menu import MAIN_MENU_TEXT, MenuStates, _main_menu_kb
        await state.clear()
        try:
            await callback.message.edit_text(MAIN_MENU_TEXT, reply_markup=_main_menu_kb())
        except Exception:
            await callback.message.answer(MAIN_MENU_TEXT, reply_markup=_main_menu_kb())
        await state.set_state(MenuStates.main_menu)
        return

    await state.set_state(prev_state)
    await _send_step_prompt(callback, state)


# ═══ REMINDER CALLBACKS ═══

@router.callback_query(F.data.startswith("remind_"))
async def on_reminder_choice(callback: CallbackQuery, state: FSMContext):
    """Handle reminder time selection."""
    if callback.data == "remind_continue":
        await callback.answer()
        # Reset reminder tracking + re-send current step prompt
        await state.update_data(reminder_prompt_sent_at=None, reminder_scheduled_at=None)
        await _send_step_prompt(callback, state)
        return

    # Parse minutes from callback: remind_30, remind_60, remind_180, remind_720
    try:
        minutes = int(callback.data.removeprefix("remind_"))
    except ValueError:
        await callback.answer("Invalid option")
        return

    from datetime import datetime, timedelta
    remind_at = (datetime.utcnow() + timedelta(minutes=minutes)).isoformat()
    await state.update_data(reminder_scheduled_at=remind_at)
    await callback.answer("Got it! I'll remind you then 🔔")

    labels = {30: "30 minutes", 60: "1 hour", 180: "3 hours", 720: "12 hours"}
    label = labels.get(minutes, f"{minutes} minutes")
    try:
        await callback.message.edit_text(
            f"No problem! I'll send you a reminder in {label}. See you soon! 👋"
        )
    except Exception:
        pass


# ═══ CATCH-ALL: text in callback-based states ═══

@router.message(OperatorForm.waiting_has_pc)
@router.message(OperatorForm.waiting_no_pc_followup)
@router.message(OperatorForm.waiting_study_work)
@router.message(OperatorForm.waiting_cpu_simple_age)
@router.message(OperatorForm.waiting_cpu_simple_usage)
@router.message(OperatorForm.waiting_gpu_simple_gaming)
async def catch_text_in_button_states(message: Message, state: FSMContext):
    """Handle free text when buttons are expected."""
    handled = await _handle_possible_question(message, state)
    if not handled:
        await message.answer("Please use the buttons above to answer. 👆")


@router.message(OperatorForm.waiting_english)
async def process_english_text(message: Message, state: FSMContext):
    """Accept numeric 1-10 rating for English level."""
    if await _handle_possible_question(message, state):
        return

    text = (message.text or "").strip()
    # Try to parse a number 1-10
    num = None
    for word in text.split():
        if word.isdigit():
            num = int(word)
            break
    if num is None:
        try:
            num = int(text)
        except ValueError:
            pass

    if num is not None and 1 <= num <= 10:
        # Map number to level: 1-3 = Beginner, 4-5 = B1, 6-7 = B2, 8-9 = C1, 10 = Native
        if num <= 3:
            eng_val = "Beginner"
        elif num <= 5:
            eng_val = "B1"
        elif num <= 7:
            eng_val = "B2"
        elif num <= 9:
            eng_val = "C1"
        else:
            eng_val = "Native"

        await state.update_data(english_level=eng_val)
        await _track_event(message.from_user.id, "step_completed", "english", {"level": eng_val, "raw": num})
        data = await state.get_data()
        await notion_leads.on_english(data.get("notion_page_id"), eng_val)

        await message.answer(
            "You're doing great! Almost halfway there.\n\n"
            "People like you are already earning with us:\n"
            "  Maria from Manila — $250/week after 2 months\n"
            "  Emeka from Lagos — started from zero, now $200/week\n\n"
            "Just a few more questions about your setup!"
        )

        await state.set_state(OperatorForm.waiting_pc_confidence)
        kb = InlineKeyboardMarkup(inline_keyboard=[_back_row()])
        await message.answer(
            f"{_progress(6)}\n\n"
            "How comfortable are you with Windows?\n\n"
            "For example: installing programs, troubleshooting, changing settings?\n\n"
            "You can rate yourself from 1 to 10.",
            reply_markup=kb,
        )
        return

    await message.answer("Please use the buttons above or rate yourself 1-10. 👆")


# ═══ STEP 1: Name ═══

@router.message(OperatorForm.waiting_name)
async def process_name(message: Message, state: FSMContext):
    name = message.text.strip() if message.text else ""

    if await _handle_possible_question(message, state):
        return

    if len(name) < 2 or len(name) > 100:
        await message.answer("Please enter your full name (e.g., John Smith).")
        return

    await state.update_data(name=name)
    await _track_event(message.from_user.id, "step_completed", "name", {"name": name})
    data = await state.get_data()
    await notion_leads.on_name(data.get("notion_page_id"), name)
    await state.set_state(OperatorForm.waiting_has_pc)
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="🖥️ Yes, PC/Desktop", callback_data="pc_desktop"),
            InlineKeyboardButton(text="💻 Yes, Laptop", callback_data="pc_laptop"),
        ],
        [InlineKeyboardButton(text="❌ No", callback_data="pc_no")],
        _back_row(),
    ])
    await message.answer(
        f"Nice to meet you, {name.split()[0]}! 🙂\n\n"
        f"{_progress(2)}\n\n"
        "Do you have a Windows PC or laptop?",
        reply_markup=kb,
    )


# ═══ STEP 2: PC Check ═══

@router.callback_query(OperatorForm.waiting_has_pc, F.data.startswith("pc_"))
async def process_has_pc(callback: CallbackQuery, state: FSMContext):
    choice = callback.data.removeprefix("pc_")
    await callback.answer()

    if choice == "no":
        await state.update_data(has_pc=False)
        await _track_event(callback.from_user.id, "step_completed", "has_pc", {"has_pc": False})
        kb = InlineKeyboardMarkup(inline_keyboard=[
            [
                InlineKeyboardButton(text="✅ Yes, within 1-2 weeks", callback_data="nopc_soon"),
                InlineKeyboardButton(text="🤷 No plans yet", callback_data="nopc_no"),
            ],
            _back_row(),
        ])
        await callback.message.answer(
            "I see. This role requires a Windows PC or laptop for the streaming software.\n\n"
            "Are you planning to get one in the near future?",
            reply_markup=kb,
        )
        await state.set_state(OperatorForm.waiting_no_pc_followup)
        return

    await state.update_data(has_pc=True, pc_type=choice)
    await _track_event(callback.from_user.id, "step_completed", "has_pc", {"has_pc": True, "pc_type": choice})
    data = await state.get_data()
    await notion_leads.on_has_pc(data.get("notion_page_id"), True)
    await state.set_state(OperatorForm.waiting_age)
    kb = InlineKeyboardMarkup(inline_keyboard=[_back_row()])
    await callback.message.answer(f"Great! 👍\n\n{_progress(3)}\n\nHow old are you?", reply_markup=kb)


@router.callback_query(OperatorForm.waiting_no_pc_followup, F.data.startswith("nopc_"))
async def process_no_pc_followup(callback: CallbackQuery, state: FSMContext):
    choice = callback.data.removeprefix("nopc_")
    await callback.answer()

    await state.update_data(no_pc_plan=choice)
    await _track_event(callback.from_user.id, "step_completed", "no_pc_followup", {"plan": choice})

    # Continue to age instead of declining
    await state.set_state(OperatorForm.waiting_age)
    kb = InlineKeyboardMarkup(inline_keyboard=[_back_row()])
    await callback.message.answer(
        "Got it, no worries! Let's continue — we'll figure out the PC situation later.\n\n"
        f"{_progress(3)}\n\nHow old are you?",
        reply_markup=kb,
    )


# ═══ STEP 3: Age ═══

@router.message(OperatorForm.waiting_age)
async def process_age(message: Message, state: FSMContext):
    text = message.text.strip() if message.text else ""

    if await _handle_possible_question(message, state):
        return

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

    await state.update_data(age=age)
    await _track_event(message.from_user.id, "step_completed", "age", {"age": age})
    data = await state.get_data()
    await notion_leads.on_age(data.get("notion_page_id"), age)
    await state.set_state(OperatorForm.waiting_study_work)
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="💼 Working", callback_data="study_working")],
        [InlineKeyboardButton(text="🎓 Student (online classes)", callback_data="study_distance")],
        [InlineKeyboardButton(text="🏫 Student (on campus)", callback_data="study_inperson")],
        [InlineKeyboardButton(text="🏠 Neither", callback_data="study_neither")],
        _back_row(),
    ])
    await message.answer(f"{_progress(4)}\n\nAre you currently studying or working?", reply_markup=kb)


# ═══ STEP 4: Study/Work Status ═══

@router.callback_query(OperatorForm.waiting_study_work, F.data.startswith("study_"))
async def process_study_work(callback: CallbackQuery, state: FSMContext):
    status = callback.data.removeprefix("study_")
    await callback.answer()

    mapped = {"working": "working", "distance": "student_distance", "inperson": "student_inperson", "neither": "neither"}
    study_val = mapped.get(status, status)
    await state.update_data(study_status=study_val)
    await _track_event(callback.from_user.id, "step_completed", "study_work", {"status": study_val})

    await state.set_state(OperatorForm.waiting_english)
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="📗 Basic", callback_data="eng_beginner"),
            InlineKeyboardButton(text="📘 Can hold a conversation", callback_data="eng_b1"),
        ],
        [
            InlineKeyboardButton(text="📙 Comfortable", callback_data="eng_b2"),
            InlineKeyboardButton(text="📕 Fluent", callback_data="eng_c1"),
        ],
        [InlineKeyboardButton(text="🌟 Native speaker", callback_data="eng_native")],
        _back_row(),
    ])
    await callback.message.answer(
        f"{_progress(5)}\n\n"
        "How well do you speak English?\n\n"
        "We need at least conversational level — you'll be moderating English chats.\n\n"
        "You can also rate yourself from 1 to 10.",
        reply_markup=kb,
    )


# ═══ STEP 5: English Level ═══

@router.callback_query(OperatorForm.waiting_english, F.data.startswith("eng_"))
async def process_english(callback: CallbackQuery, state: FSMContext):
    level = callback.data.removeprefix("eng_")
    await callback.answer()

    level_map = {"beginner": "Beginner", "b1": "B1", "b2": "B2", "c1": "C1", "native": "Native"}
    eng_val = level_map.get(level, level)
    await state.update_data(english_level=eng_val)
    await _track_event(callback.from_user.id, "step_completed", "english", {"level": eng_val})
    data = await state.get_data()
    await notion_leads.on_english(data.get("notion_page_id"), eng_val)

    # Social proof — rebuild trust before hardware steps
    await callback.message.answer(
        "You're doing great! Almost halfway there.\n\n"
        "People like you are already earning with us:\n"
        "  Maria from Manila — $250/week after 2 months\n"
        "  Emeka from Lagos — started from zero, now $200/week\n\n"
        "Just a few more questions about your setup!"
    )

    await state.set_state(OperatorForm.waiting_pc_confidence)
    kb = InlineKeyboardMarkup(inline_keyboard=[_back_row()])
    await callback.message.answer(
        f"{_progress(6)}\n\n"
        "How comfortable are you with Windows?\n\n"
        "For example: installing programs, troubleshooting, changing settings?\n\n"
        "You can rate yourself from 1 to 10.",
        reply_markup=kb,
    )


# ═══ STEP 6: PC Confidence ═══

@router.message(OperatorForm.waiting_pc_confidence)
async def process_pc_confidence(message: Message, state: FSMContext):
    if await _handle_possible_question(message, state):
        return

    confidence = message.text.strip()
    await state.update_data(pc_confidence=confidence)
    await _track_event(message.from_user.id, "step_completed", "pc_confidence", {"value": confidence})
    await state.set_state(OperatorForm.waiting_cpu)
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🤔 Not sure", callback_data="cpu_skip")],
        _back_row(),
    ])
    await message.answer(
        f"{_progress(7)}\n\n"
        "What is your processor (CPU)?\n\n"
        "How to check:\n"
        "Settings > System > About > look for 'Processor'\n\n"
        "Example: Intel Core i5-12400 or AMD Ryzen 5 5600\n\n"
        "Not sure? Tap the button — we'll ask a few simple questions instead.",
        reply_markup=kb,
    )


# ═══ STEP 7: CPU ═══

@router.callback_query(OperatorForm.waiting_cpu, F.data == "cpu_skip")
async def process_cpu_skip(callback: CallbackQuery, state: FSMContext):
    """CPU skip → ask simplified questions instead."""
    await callback.answer()
    await state.set_state(OperatorForm.waiting_cpu_simple_age)
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🆕 Less than 2 years", callback_data="pcage_new")],
        [InlineKeyboardButton(text="📅 2-4 years", callback_data="pcage_mid")],
        [InlineKeyboardButton(text="📆 5+ years", callback_data="pcage_old")],
        [InlineKeyboardButton(text="🤔 Not sure", callback_data="pcage_unsure")],
        _back_row(),
    ])
    await callback.message.answer(
        f"{_progress(7)} — No worries! A few quick questions instead.\n\n"
        "How old is your computer?",
        reply_markup=kb,
    )


# ═══ STEP 7a: Simplified CPU — PC Age ═══

@router.callback_query(OperatorForm.waiting_cpu_simple_age, F.data.startswith("pcage_"))
async def process_cpu_simple_age(callback: CallbackQuery, state: FSMContext):
    choice = callback.data.removeprefix("pcage_")
    await callback.answer()

    age_labels = {"new": "Less than 2 years", "mid": "2-4 years", "old": "5+ years", "unsure": "Not sure"}
    await state.update_data(pc_age_estimate=age_labels.get(choice, choice))

    await state.set_state(OperatorForm.waiting_cpu_simple_usage)
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🎮 Gaming", callback_data="pcuse_gaming")],
        [InlineKeyboardButton(text="💼 Work / Office", callback_data="pcuse_work")],
        [InlineKeyboardButton(text="🌐 Browsing / Social media", callback_data="pcuse_browsing")],
        [InlineKeyboardButton(text="🎨 Video editing / Design", callback_data="pcuse_creative")],
        _back_row(),
    ])
    await callback.message.answer(
        f"{_progress(7)}\n\n"
        "What do you mainly use your computer for?",
        reply_markup=kb,
    )


# ═══ STEP 7b: Simplified CPU — Usage → proceed to GPU ═══

@router.callback_query(OperatorForm.waiting_cpu_simple_usage, F.data.startswith("pcuse_"))
async def process_cpu_simple_usage(callback: CallbackQuery, state: FSMContext):
    choice = callback.data.removeprefix("pcuse_")
    await callback.answer()

    usage_labels = {"gaming": "Gaming", "work": "Work/Office", "browsing": "Browsing/Social media", "creative": "Video editing/Design"}
    usage = usage_labels.get(choice, choice)
    await state.update_data(pc_usage=usage)

    # Compose a descriptive CPU string for AI scoring
    data = await state.get_data()
    pc_age = data.get("pc_age_estimate", "unknown")
    cpu_desc = f"Not sure (PC age: {pc_age}, Usage: {usage})"
    await state.update_data(cpu_model=cpu_desc)
    await _track_event(callback.from_user.id, "step_completed", "cpu", {"cpu_model": cpu_desc, "method": "simplified"})

    # Proceed to GPU
    await state.set_state(OperatorForm.waiting_gpu)
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🤔 Not sure", callback_data="gpu_skip")],
        _back_row(),
    ])
    await callback.message.answer(
        f"{_progress(8)}\n\n"
        "What is your graphics card (GPU)?\n\n"
        "How to check:\n"
        "Settings > System > Display > Advanced display > look for GPU info\n\n"
        "Example: NVIDIA GeForce RTX 3060 or AMD Radeon RX 6600\n\n"
        "Not sure? Tap the button below.",
        reply_markup=kb,
    )


@router.message(OperatorForm.waiting_cpu)
async def process_cpu(message: Message, state: FSMContext):
    if await _handle_possible_question(message, state):
        return

    if message.photo:
        await message.answer("📸 Reading your screenshot...")
        cpu = await _extract_from_photo(
            message,
            "This is a screenshot showing CPU/processor info (Task Manager, System Info, or About PC). "
            "Extract the CPU model name. Reply with just the CPU model, e.g. 'Intel Core i7-12700K' or 'AMD Ryzen 5 5600X'.",
        )
        if cpu is None:
            await message.answer(
                "Sorry, I couldn't read that. Could you type your CPU model instead?\n\n"
                "Example: Intel Core i5-12400 or AMD Ryzen 5 5600X"
            )
            return
        await message.answer(f"Got it: {cpu}")
    elif message.text:
        cpu = message.text.strip()
    else:
        await message.answer("Please type your CPU model or send a screenshot from Task Manager / System Info.")
        return
    await state.update_data(cpu_model=cpu)
    await _track_event(message.from_user.id, "step_completed", "cpu", {"cpu_model": cpu})
    await state.set_state(OperatorForm.waiting_gpu)
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🤔 I'm not sure / skip", callback_data="gpu_skip")],
        _back_row(),
    ])
    await message.answer(
        f"{_progress(8)}\n\n"
        "What is your graphics card (GPU)?\n\n"
        "How to check:\n"
        "Settings > System > Display > Advanced display\n\n"
        "Example: NVIDIA GeForce RTX 3060 or AMD Radeon RX 6600\n\n"
        "Not sure? Tap 'skip' — we'll check during your interview.",
        reply_markup=kb,
    )


# ═══ STEP 8: GPU ═══

@router.callback_query(OperatorForm.waiting_gpu, F.data == "gpu_skip")
async def process_gpu_skip(callback: CallbackQuery, state: FSMContext):
    """GPU skip → ask simplified gaming question."""
    await callback.answer()
    await state.set_state(OperatorForm.waiting_gpu_simple_gaming)
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🎮 Yes, modern games (GTA, Fortnite)", callback_data="game_modern")],
        [InlineKeyboardButton(text="🕹️ Yes, but only simple/old games", callback_data="game_basic")],
        [InlineKeyboardButton(text="❌ No / Never tried", callback_data="game_no")],
        [InlineKeyboardButton(text="🤔 Not sure", callback_data="game_unsure")],
        _back_row(),
    ])
    await callback.message.answer(
        f"{_progress(8)} — One more quick question.\n\n"
        "Can your computer run video games?",
        reply_markup=kb,
    )


# ═══ STEP 8a: Simplified GPU — Gaming capability ═══

@router.callback_query(OperatorForm.waiting_gpu_simple_gaming, F.data.startswith("game_"))
async def process_gpu_simple_gaming(callback: CallbackQuery, state: FSMContext):
    choice = callback.data.removeprefix("game_")
    await callback.answer()

    gaming_labels = {
        "modern": "Runs modern games (GTA, Fortnite)",
        "basic": "Only simple/old games",
        "no": "No / Never tried gaming",
        "unsure": "Not sure",
    }
    gaming = gaming_labels.get(choice, choice)
    await state.update_data(pc_gaming=gaming)

    # Compose descriptive GPU string for AI scoring
    gpu_desc = f"Not sure (Gaming: {gaming})"
    await state.update_data(gpu_model=gpu_desc)

    # Run hardware check with available data
    data = await state.get_data()
    cpu = data.get("cpu_model", "")
    if "Not sure" in cpu:
        # Both simplified — estimate compatibility from answers
        pc_age = data.get("pc_age_estimate", "unknown")
        pc_usage = data.get("pc_usage", "unknown")
        # Heuristic: new gaming PC = likely compatible
        likely_ok = (
            (pc_age in ("Less than 2 years", "2-4 years") and pc_usage == "Gaming")
            or (pc_age == "Less than 2 years" and pc_usage in ("Video editing/Design", "Work/Office"))
            or (choice == "modern")
        )
        await state.update_data(
            hardware_compatible=True if likely_ok else None,
            cpu_status=f"estimated from answers (age: {pc_age}, usage: {pc_usage})",
            gpu_status=f"estimated from answers (gaming: {gaming})",
        )
    else:
        hw_result = quick_check(cpu, "UNKNOWN")
        await state.update_data(
            hardware_compatible=None,
            cpu_status=hw_result.cpu_reason,
            gpu_status=f"estimated from answers (gaming: {gaming})",
        )

    await _track_event(callback.from_user.id, "step_completed", "gpu", {"gpu_model": gpu_desc, "method": "simplified"})

    # Proceed to internet
    await state.set_state(OperatorForm.waiting_internet)
    kb = InlineKeyboardMarkup(inline_keyboard=[_back_row()])
    await callback.message.answer(
        f"{_progress(9)}\n\n"
        "What is your internet speed?\n\n"
        "You can check at speedtest.net\n\n"
        "Also — are you on WiFi or plugged in with a cable?",
        reply_markup=kb,
    )


@router.message(OperatorForm.waiting_gpu)
async def process_gpu(message: Message, state: FSMContext):
    if await _handle_possible_question(message, state):
        return

    if message.photo:
        await message.answer("📸 Reading your screenshot...")
        gpu = await _extract_from_photo(
            message,
            "This is a screenshot showing GPU/graphics card info (Task Manager, Device Manager, or Display settings). "
            "Extract the GPU model name. Reply with just the GPU model, e.g. 'NVIDIA GeForce RTX 3060' or 'AMD Radeon RX 6600'.",
        )
        if gpu is None:
            await message.answer(
                "Sorry, I couldn't read that. Could you type your GPU model instead?\n\n"
                "Example: NVIDIA GeForce GTX 1650 or AMD Radeon RX 580"
            )
            return
        await message.answer(f"Got it: {gpu}")
    elif message.text:
        gpu = message.text.strip()
    else:
        await message.answer("Please type your GPU model or send a screenshot.")
        return
    await state.update_data(gpu_model=gpu)

    data = await state.get_data()
    hw_result = quick_check(data["cpu_model"], gpu)
    await state.update_data(
        hardware_compatible=hw_result.compatible,
        cpu_status=hw_result.cpu_reason,
        gpu_status=hw_result.gpu_reason,
    )
    await _track_event(message.from_user.id, "step_completed", "gpu", {
        "gpu_model": gpu, "hw_compatible": hw_result.compatible,
        "cpu_reason": hw_result.cpu_reason, "gpu_reason": hw_result.gpu_reason,
    })

    if not hw_result.compatible:
        issues = []
        if not hw_result.cpu_ok:
            issues.append(f"CPU: {hw_result.cpu_reason}")
        if not hw_result.gpu_ok:
            issues.append(f"GPU: {hw_result.gpu_reason}")
        await state.update_data(hardware_issues="\n".join(issues))

    await state.set_state(OperatorForm.waiting_internet)
    kb = InlineKeyboardMarkup(inline_keyboard=[_back_row()])
    await message.answer(
        "What is your internet speed? (minimum 100 Mbps required)\n\n"
        "You can check at speedtest.net\n\n"
        "Also — do you have a LAN (ethernet) connection or Wi-Fi only?",
        reply_markup=kb,
    )


# ═══ STEP 9: Internet Speed ═══

@router.message(OperatorForm.waiting_internet)
async def process_internet(message: Message, state: FSMContext):
    if await _handle_possible_question(message, state):
        return

    if message.photo:
        await message.answer("📸 Reading your speed test screenshot...")
        inet = await _extract_from_photo(
            message,
            "This is a screenshot of an internet speed test. "
            "Extract download speed, upload speed, and ping. "
            "Reply in format: 'Download: X Mbps, Upload: Y Mbps, Ping: Z ms'. "
            "Add ISP name and connection type if visible. Only return extracted data.",
        )
        if inet is None:
            await message.answer(
                "Sorry, I couldn't read that screenshot.\n"
                "Could you type your internet speed instead?\n\n"
                "For example: Download 150 Mbps, Upload 50 Mbps, Wi-Fi"
            )
            return
        await message.answer(f"Got it: {inet}")
    elif message.text:
        inet = message.text.strip()
    else:
        await message.answer("Please type your internet speed or send a screenshot of your speed test.")
        return

    await state.update_data(internet_speed=inet)
    await _track_event(message.from_user.id, "step_completed", "internet", {"value": inet})
    await state.set_state(OperatorForm.waiting_start_date)
    kb = InlineKeyboardMarkup(inline_keyboard=[_back_row()])
    await message.answer(
        "When would you be ready to start?\n\n"
        "We can schedule your interview and start training the same day!",
        reply_markup=kb,
    )


# ═══ STEP 10: Start Date ═══

@router.message(OperatorForm.waiting_start_date)
async def process_start_date(message: Message, state: FSMContext):
    if await _handle_possible_question(message, state):
        return

    sdate = message.text.strip()
    await state.update_data(start_date=sdate)
    await _track_event(message.from_user.id, "step_completed", "start_date", {"value": sdate})
    await state.set_state(OperatorForm.waiting_contact)
    kb = InlineKeyboardMarkup(inline_keyboard=[_back_row()])
    await message.answer(
        "Last question! 🙂\n\n"
        "Please share your contact for the interview:\n"
        "• Telegram @username (preferred)\n"
        "• Or WhatsApp number",
        reply_markup=kb,
    )


# ═══ STEP 11: Contact → Screening ═══

@router.message(OperatorForm.waiting_contact)
async def process_contact(message: Message, state: FSMContext):
    if await _handle_possible_question(message, state):
        return

    contact = message.text.strip()
    await state.update_data(contact_info=contact)
    await _track_event(message.from_user.id, "step_completed", "contact", {"value": contact})
    data = await state.get_data()

    # AI screening (with fallback if AI unavailable)
    await message.answer(
        "Thank you for completing the application! 🎉\n\n"
        "I'm reviewing your information now..."
    )

    import asyncio
    await asyncio.sleep(10)

    try:
        result = await screen_candidate(
            name=data.get("name", "N/A"),
            has_pc=data.get("has_pc"),
            age=data.get("age"),
            study_status=data.get("study_status", "N/A"),
            english_level=data.get("english_level", "N/A"),
            pc_confidence=data.get("pc_confidence", "N/A"),
            cpu_model=data.get("cpu_model", "N/A"),
            gpu_model=data.get("gpu_model", "N/A"),
            cpu_status=data.get("cpu_status", "N/A"),
            gpu_status=data.get("gpu_status", "N/A"),
            hardware_compatible=data.get("hardware_compatible"),
            internet_speed=data.get("internet_speed", "N/A"),
            start_date=data.get("start_date", "N/A"),
            contact_info=data.get("contact_info", "N/A"),
            tg_username=message.from_user.username or "N/A",
        )
    except Exception:
        logger.exception("AI screening failed — using fallback")
        result = ScreeningResult(
            english_score=0, hardware_score=0, availability_score=0,
            motivation_score=0, experience_score=0, overall_score=0,
            recommendation="MAYBE",
            reasoning="AI screening unavailable — manual review needed",
            suggested_response=(
                "Thank you for applying! 🎉\n\n"
                "Our team will review your application and get back to you "
                "within 24 hours to schedule your interview.\n\n"
                "Talk to you soon!"
            ),
        )

    await _track_event(message.from_user.id, "completed", "screening", {
        "score": result.overall_score,
        "recommendation": result.recommendation,
    })

    await _save_candidate(
        message, data,
        status="screened",
        score=result.overall_score,
        recommendation=result.recommendation,
        notes=result.reasoning,
    )

    await notion_leads.on_complete(
        page_id=data.get("notion_page_id"),
        tg_id=message.from_user.id,
        tg_username=message.from_user.username,
        data=data,
        recommendation=result.recommendation,
        score=result.overall_score,
        notes=result.reasoning,
    )

    # PASS → auto-start interview booking (AI decided to invite)
    # MAYBE/REJECT → admin decides via button
    if result.recommendation == "PASS":
        from bot.handlers.interview_booking import start_booking
        await start_booking(message, state, message.from_user.id)
    else:
        await state.clear()
        await message.answer(result.suggested_response)

    await _notify_admin(message, data, result)
    await _send_to_n8n(message, data, result)


# ═══ DB SAVE ═══

async def _save_candidate(message, data, status="new", score=None, recommendation=None, notes=None, user=None):
    from_user = user or message.from_user
    try:
        async with async_session() as session:
            # Upsert: update existing candidate or create new
            result = await session.execute(
                select(Candidate).where(Candidate.tg_user_id == from_user.id)
            )
            candidate = result.scalar_one_or_none()

            if candidate:
                # Update existing record
                candidate.tg_username = from_user.username
                candidate.name = data.get("name", "Unknown")
                candidate.candidate_type = data.get("candidate_type", "operator")
                candidate.has_pc = data.get("has_pc")
                candidate.age = data.get("age")
                candidate.study_status = data.get("study_status")
                candidate.english_level = data.get("english_level")
                candidate.pc_confidence = data.get("pc_confidence")
                candidate.cpu_model = data.get("cpu_model")
                candidate.gpu_model = data.get("gpu_model")
                candidate.hardware_compatible = data.get("hardware_compatible")
                candidate.internet_speed = data.get("internet_speed")
                candidate.start_date = data.get("start_date")
                candidate.contact_info = data.get("contact_info")
                candidate.score = score
                candidate.recommendation = recommendation
                candidate.status = status
                candidate.notes = notes
            else:
                # Create new record
                candidate = Candidate(
                    tg_user_id=from_user.id,
                    tg_username=from_user.username,
                    name=data.get("name", "Unknown"),
                    candidate_type=data.get("candidate_type", "operator"),
                    has_pc=data.get("has_pc"),
                    age=data.get("age"),
                    study_status=data.get("study_status"),
                    english_level=data.get("english_level"),
                    pc_confidence=data.get("pc_confidence"),
                    cpu_model=data.get("cpu_model"),
                    gpu_model=data.get("gpu_model"),
                    hardware_compatible=data.get("hardware_compatible"),
                    internet_speed=data.get("internet_speed"),
                    start_date=data.get("start_date"),
                    contact_info=data.get("contact_info"),
                    referrer_tg_id=data.get("referrer_tg_id"),
                    utm_source=data.get("utm_source"),
                    score=score,
                    recommendation=recommendation,
                    status=status,
                    notes=notes,
                )
                session.add(candidate)

            await session.commit()
            logger.info("Saved candidate %s (tg_id=%s, status=%s)", data.get("name"), from_user.id, status)
    except Exception:
        logger.exception("Failed to save candidate to DB")


# ═══ ADMIN NOTIFICATION ═══

async def _notify_admin(message, data, result):
    icon = {"PASS": "🟢", "MAYBE": "🟡", "REJECT": "🔴"}.get(result.recommendation, "❓")

    # Build flags for issues admin should check
    flags = []
    if not data.get("has_pc"):
        flags.append("⚠️ NO PC")
    if data.get("no_pc_plan"):
        flags.append(f"PC plan: {data.get('no_pc_plan')}")
    age = data.get("age")
    if age and age < 18:
        flags.append("⚠️ UNDERAGE")
    if data.get("study_status") == "student_inperson":
        flags.append("⚠️ IN-PERSON STUDENT")
    if data.get("english_level") == "Beginner":
        flags.append("⚠️ BASIC ENGLISH")
    if data.get("hardware_compatible") is False:
        flags.append("⚠️ HW INCOMPATIBLE")
    if data.get("hardware_compatible") is None:
        flags.append("⚠️ HW NOT VERIFIED")
    if data.get("pc_age_estimate") or data.get("pc_gaming"):
        flags.append("ℹ️ HW ESTIMATED (simplified answers)")
    flags_str = " | ".join(flags) if flags else "None"

    admin_text = (
        f"[OPERATOR] {icon} {result.recommendation} — Score: {result.overall_score}/100\n"
        f"Flags: {flags_str}\n\n"
        f"Name: {data.get('name', 'N/A')}\n"
        f"TG: @{message.from_user.username or 'N/A'} (ID: {message.from_user.id})\n"
        f"Age: {data.get('age', 'N/A')} | English: {data.get('english_level', 'N/A')}\n"
        f"Study/Work: {data.get('study_status', 'N/A')}\n"
        f"PC: {'Yes (' + data.get('pc_type', '?') + ')' if data.get('has_pc') else 'No'}\n"
        f"CPU: {data.get('cpu_model', 'N/A')}\n"
        f"GPU: {data.get('gpu_model', 'N/A')}\n"
        f"HW check: {data.get('cpu_status', 'N/A')} / {data.get('gpu_status', 'N/A')}\n"
        f"Internet: {data.get('internet_speed', 'N/A')}\n"
        f"Start: {data.get('start_date', 'N/A')}\n"
        f"Contact: {data.get('contact_info', 'N/A')}\n"
        f"{'Referred by: ' + str(data.get('referrer_tg_id')) + chr(10) if data.get('referrer_tg_id') else ''}"
        f"{'Source: ' + data.get('utm_source', '') + chr(10) if data.get('utm_source') else ''}\n"
        f"AI: HW={result.hardware_score} Eng={result.english_score} "
        f"Avail={result.availability_score} Motiv={result.motivation_score} "
        f"Exp={result.experience_score}\n"
        f"Reasoning: {result.reasoning}"
    )
    # PASS: booking auto-started, no Interview button needed
    # MAYBE/REJECT: admin can manually invite via Interview button
    if result.recommendation == "PASS":
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
        logger.exception("Failed to notify admin")


# ═══ N8N WEBHOOK ═══

async def _send_to_n8n(message, data, result):
    if not config.N8N_WEBHOOK_URL:
        return
    try:
        async with aiohttp.ClientSession() as session:
            await session.post(
                f"{config.N8N_WEBHOOK_URL}/new-application",
                json={
                    "telegram_user_id": message.from_user.id,
                    "telegram_username": message.from_user.username,
                    "candidate_type": "operator",
                    "name": data.get("name"),
                    "has_pc": data.get("has_pc"),
                    "age": data.get("age"),
                    "study_status": data.get("study_status"),
                    "english_level": data.get("english_level"),
                    "cpu_model": data.get("cpu_model"),
                    "gpu_model": data.get("gpu_model"),
                    "hardware_compatible": data.get("hardware_compatible"),
                    "internet_speed": data.get("internet_speed"),
                    "start_date": data.get("start_date"),
                    "contact_info": data.get("contact_info"),
                    "score": result.overall_score,
                    "recommendation": result.recommendation,
                },
                timeout=aiohttp.ClientTimeout(total=5),
            )
    except Exception:
        logger.debug("n8n webhook not available — skipping")
