"""11-step FSM flow for operator (Live Stream Moderator) qualification.

Steps: name → PC → age → study/work → english → PC confidence →
       CPU → GPU → internet → start date → contact

Features:
- Objection auto-handling at every step
- Unknown questions forwarded to admin (admin replies via bot)
- Candidate saved to DB at the end
- AI screening via Claude
"""

import logging

import aiohttp
from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup, Message

from bot.config import config
from bot.database import async_session
from bot.database.models import Candidate
from bot.services.followup import (
    DECLINE_ENGLISH,
    DECLINE_HARDWARE,
    DECLINE_NO_PC,
    DECLINE_STUDENT_INPERSON,
    DECLINE_UNDERAGE,
)
from bot.services.hardware_checker import quick_check
from bot.services.objection_handler import detect_objection, get_response
from bot.services.screener import screen_candidate

logger = logging.getLogger(__name__)
router = Router()


class OperatorForm(StatesGroup):
    waiting_name = State()
    waiting_has_pc = State()
    waiting_no_pc_followup = State()
    waiting_age = State()
    waiting_study_work = State()
    waiting_english = State()
    waiting_pc_confidence = State()
    waiting_cpu = State()
    waiting_gpu = State()
    waiting_internet = State()
    waiting_start_date = State()
    waiting_contact = State()


# ═══ QUESTION / OBJECTION HANDLING ═══

async def _handle_possible_question(message: Message, state: FSMContext) -> bool:
    """Check if message is a question/objection. Handle it and return True, or return False.

    Only triggers on messages that look like questions/objections (contain '?' or are
    long enough to be conversational), not short factual answers to step questions.
    """
    text = message.text.strip() if message.text else ""
    if not text:
        return False

    has_question_mark = "?" in text
    is_conversational = len(text) > 40

    # 1. Try objection handler — only on conversational messages or explicit questions
    if has_question_mark or is_conversational:
        objection = detect_objection(text)
        if objection:
            response = get_response(objection)
            if response:
                await message.answer(response)
                await _remind_current_step(message, state)
                return True

    # 2. If text contains "?" → likely a question → forward to admin
    if has_question_mark:
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
    await _remind_current_step(message, state)


async def _remind_current_step(message: Message, state: FSMContext):
    """Re-send the current step's prompt after handling a question."""
    current = await state.get_state()

    # Text-based state prompts
    text_prompts = {
        OperatorForm.waiting_name.state: "What is your full name?",
        OperatorForm.waiting_age.state: "How old are you?",
        OperatorForm.waiting_pc_confidence.state: (
            "Do you consider yourself a confident PC user?\n\n"
            "For example: installing programs, troubleshooting, Windows settings?"
        ),
        OperatorForm.waiting_cpu.state: (
            "What is your processor (CPU) model?\n\n"
            "Press Win+R → type 'dxdiag' → Enter → look at 'Processor'"
        ),
        OperatorForm.waiting_gpu.state: (
            "What is your graphics card (GPU)?\n\n"
            "In dxdiag → 'Display' tab → 'Name' under Device"
        ),
        OperatorForm.waiting_internet.state: (
            "What is your internet speed? (minimum 100 Mbps)\n"
            "Check at speedtest.net. Also — LAN or Wi-Fi?"
        ),
        OperatorForm.waiting_start_date.state: "When would you be ready to start?",
        OperatorForm.waiting_contact.state: (
            "Please share your contact for the interview:\n"
            "• Telegram @username (preferred)\n"
            "• Or WhatsApp number"
        ),
    }

    prompt = text_prompts.get(current)
    if prompt:
        await message.answer(prompt)
        return

    # Callback-based state prompts (re-send with keyboard)
    if current == OperatorForm.waiting_has_pc.state:
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [
                InlineKeyboardButton(text="Yes, PC/Desktop", callback_data="pc_desktop"),
                InlineKeyboardButton(text="Yes, Laptop", callback_data="pc_laptop"),
            ],
            [InlineKeyboardButton(text="No", callback_data="pc_no")],
        ])
        await message.answer(
            "Do you have a personal PC or laptop? (Windows only — MacBooks are not supported)",
            reply_markup=keyboard,
        )
    elif current == OperatorForm.waiting_no_pc_followup.state:
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [
                InlineKeyboardButton(text="Yes, within 1-2 weeks", callback_data="nopc_soon"),
                InlineKeyboardButton(text="No plans yet", callback_data="nopc_no"),
            ],
        ])
        await message.answer(
            "Are you planning to get a Windows PC in the near future?",
            reply_markup=keyboard,
        )
    elif current == OperatorForm.waiting_study_work.state:
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="Working", callback_data="study_working")],
            [InlineKeyboardButton(text="Student (distance/online)", callback_data="study_distance")],
            [InlineKeyboardButton(text="Student (in-person)", callback_data="study_inperson")],
            [InlineKeyboardButton(text="Neither", callback_data="study_neither")],
        ])
        await message.answer("Are you currently studying or working?", reply_markup=keyboard)
    elif current == OperatorForm.waiting_english.state:
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [
                InlineKeyboardButton(text="Beginner (A1-A2)", callback_data="eng_beginner"),
                InlineKeyboardButton(text="Intermediate (B1)", callback_data="eng_b1"),
            ],
            [
                InlineKeyboardButton(text="Upper-Intermediate (B2)", callback_data="eng_b2"),
                InlineKeyboardButton(text="Advanced (C1+)", callback_data="eng_c1"),
            ],
            [InlineKeyboardButton(text="Native / Fluent", callback_data="eng_native")],
        ])
        await message.answer(
            "What is your English level?\n\n"
            "B1 (Intermediate) is the minimum requirement.",
            reply_markup=keyboard,
        )


# ═══ CATCH-ALL: text in callback-based states ═══

@router.message(OperatorForm.waiting_has_pc)
@router.message(OperatorForm.waiting_no_pc_followup)
@router.message(OperatorForm.waiting_study_work)
@router.message(OperatorForm.waiting_english)
async def catch_text_in_button_states(message: Message, state: FSMContext):
    """Handle free text when buttons are expected."""
    handled = await _handle_possible_question(message, state)
    if not handled:
        await message.answer("Please use the buttons above to answer. 👆")


# ═══ STEP 1: Name ═══

@router.message(OperatorForm.waiting_name)
async def process_name(message: Message, state: FSMContext):
    name = message.text.strip() if message.text else ""

    # Check for questions/objections
    if await _handle_possible_question(message, state):
        return

    if len(name) < 2 or len(name) > 100:
        await message.answer("Please enter your full name (e.g., John Smith).")
        return

    await state.update_data(name=name)

    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="Yes, PC/Desktop", callback_data="pc_desktop"),
            InlineKeyboardButton(text="Yes, Laptop", callback_data="pc_laptop"),
        ],
        [InlineKeyboardButton(text="No", callback_data="pc_no")],
    ])
    await message.answer(
        f"Nice to meet you, {name.split()[0]}! 🙂\n\n"
        "Do you have a personal PC or laptop? (Windows only — MacBooks are not supported)",
        reply_markup=keyboard,
    )
    await state.set_state(OperatorForm.waiting_has_pc)


# ═══ STEP 2: PC Check ═══

@router.callback_query(OperatorForm.waiting_has_pc, F.data.startswith("pc_"))
async def process_has_pc(callback: CallbackQuery, state: FSMContext):
    choice = callback.data.removeprefix("pc_")
    await callback.answer()

    if choice == "no":
        await state.update_data(has_pc=False)
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [
                InlineKeyboardButton(text="Yes, within 1-2 weeks", callback_data="nopc_soon"),
                InlineKeyboardButton(text="No plans yet", callback_data="nopc_no"),
            ],
        ])
        await callback.message.answer(
            "I see. This role requires a Windows PC or laptop for the streaming software.\n\n"
            "Are you planning to get one in the near future?",
            reply_markup=keyboard,
        )
        await state.set_state(OperatorForm.waiting_no_pc_followup)
        return

    await state.update_data(has_pc=True, pc_type=choice)
    await callback.message.answer("Great! 👍\n\nHow old are you?")
    await state.set_state(OperatorForm.waiting_age)


@router.callback_query(OperatorForm.waiting_no_pc_followup, F.data.startswith("nopc_"))
async def process_no_pc_followup(callback: CallbackQuery, state: FSMContext):
    choice = callback.data.removeprefix("nopc_")
    await callback.answer()

    if choice == "soon":
        await callback.message.answer(
            "That's great! 🙂 Feel free to come back when you have your PC set up. "
            "Just send /start and we'll get you going!\n\n"
            "We'll keep your application on file. Good luck! 🍀"
        )
    else:
        await callback.message.answer(DECLINE_NO_PC)

    await state.clear()


# ═══ STEP 3: Age ═══

@router.message(OperatorForm.waiting_age)
async def process_age(message: Message, state: FSMContext):
    text = message.text.strip() if message.text else ""

    # Check for questions first
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

    if age < 18:
        await state.update_data(age=age)
        await message.answer(DECLINE_UNDERAGE)
        await _save_candidate(message, await state.get_data(), status="declined", notes="underage")
        await state.clear()
        return

    await state.update_data(age=age)

    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Working", callback_data="study_working")],
        [InlineKeyboardButton(text="Student (distance/online)", callback_data="study_distance")],
        [InlineKeyboardButton(text="Student (in-person)", callback_data="study_inperson")],
        [InlineKeyboardButton(text="Neither", callback_data="study_neither")],
    ])
    await message.answer(
        "Are you currently studying or working?",
        reply_markup=keyboard,
    )
    await state.set_state(OperatorForm.waiting_study_work)


# ═══ STEP 4: Study/Work Status ═══

@router.callback_query(OperatorForm.waiting_study_work, F.data.startswith("study_"))
async def process_study_work(callback: CallbackQuery, state: FSMContext):
    status = callback.data.removeprefix("study_")
    await callback.answer()

    if status == "inperson":
        await state.update_data(study_status="student_inperson")
        await callback.message.answer(DECLINE_STUDENT_INPERSON)
        await _save_candidate(
            callback.message, await state.get_data(),
            status="declined", notes="in-person student",
            user=callback.from_user,
        )
        await state.clear()
        return

    status_map = {"working": "working", "distance": "student_distance", "neither": "neither"}
    await state.update_data(study_status=status_map.get(status, status))

    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="Beginner (A1-A2)", callback_data="eng_beginner"),
            InlineKeyboardButton(text="Intermediate (B1)", callback_data="eng_b1"),
        ],
        [
            InlineKeyboardButton(text="Upper-Intermediate (B2)", callback_data="eng_b2"),
            InlineKeyboardButton(text="Advanced (C1+)", callback_data="eng_c1"),
        ],
        [InlineKeyboardButton(text="Native / Fluent", callback_data="eng_native")],
    ])
    await callback.message.answer(
        "What is your English level?\n\n"
        "B1 (Intermediate) is the minimum requirement — "
        "you'll be moderating English-language chats.",
        reply_markup=keyboard,
    )
    await state.set_state(OperatorForm.waiting_english)


# ═══ STEP 5: English Level ═══

@router.callback_query(OperatorForm.waiting_english, F.data.startswith("eng_"))
async def process_english(callback: CallbackQuery, state: FSMContext):
    level = callback.data.removeprefix("eng_")
    await callback.answer()

    if level == "beginner":
        await state.update_data(english_level="beginner")
        await callback.message.answer(DECLINE_ENGLISH)
        await _save_candidate(
            callback.message, await state.get_data(),
            status="declined", notes="english below B1",
            user=callback.from_user,
        )
        await state.clear()
        return

    level_map = {"b1": "B1", "b2": "B2", "c1": "C1", "native": "Native"}
    await state.update_data(english_level=level_map.get(level, level))

    await callback.message.answer(
        "Do you consider yourself a confident PC user?\n\n"
        "For example: do you install programs, troubleshoot issues, "
        "know your way around Windows settings?"
    )
    await state.set_state(OperatorForm.waiting_pc_confidence)


# ═══ STEP 6: PC Confidence ═══

@router.message(OperatorForm.waiting_pc_confidence)
async def process_pc_confidence(message: Message, state: FSMContext):
    if await _handle_possible_question(message, state):
        return

    await state.update_data(pc_confidence=message.text.strip())

    await message.answer(
        "What is your processor (CPU) model?\n\n"
        "How to check: Press Win+R → type 'dxdiag' → press Enter → "
        "look at 'Processor' line\n\n"
        "Example: Intel Core i5-12400 or AMD Ryzen 5 5600"
    )
    await state.set_state(OperatorForm.waiting_cpu)


# ═══ STEP 7: CPU ═══

@router.message(OperatorForm.waiting_cpu)
async def process_cpu(message: Message, state: FSMContext):
    cpu = message.text.strip() if message.text else ""

    if await _handle_possible_question(message, state):
        return

    await state.update_data(cpu_model=cpu)

    await message.answer(
        "What is your graphics card (GPU)?\n\n"
        "In the same dxdiag window → click 'Display' tab → "
        "look at 'Name' under Device\n\n"
        "Example: NVIDIA GeForce RTX 3060 or AMD Radeon RX 6600"
    )
    await state.set_state(OperatorForm.waiting_gpu)


# ═══ STEP 8: GPU ═══

@router.message(OperatorForm.waiting_gpu)
async def process_gpu(message: Message, state: FSMContext):
    gpu = message.text.strip() if message.text else ""

    if await _handle_possible_question(message, state):
        return

    await state.update_data(gpu_model=gpu)

    data = await state.get_data()
    hw_result = quick_check(data["cpu_model"], gpu)

    await state.update_data(
        hardware_compatible=hw_result.compatible,
        cpu_status=hw_result.cpu_reason,
        gpu_status=hw_result.gpu_reason,
    )

    if not hw_result.compatible:
        issues = []
        if not hw_result.cpu_ok:
            issues.append(f"CPU: {hw_result.cpu_reason}")
        if not hw_result.gpu_ok:
            issues.append(f"GPU: {hw_result.gpu_reason}")
        await state.update_data(hardware_issues="\n".join(issues))

    await message.answer(
        "What is your internet speed? (minimum 100 Mbps required)\n\n"
        "You can check at speedtest.net\n\n"
        "Also — do you have a LAN (ethernet) connection or Wi-Fi only?"
    )
    await state.set_state(OperatorForm.waiting_internet)


# ═══ STEP 9: Internet Speed ═══

@router.message(OperatorForm.waiting_internet)
async def process_internet(message: Message, state: FSMContext):
    if await _handle_possible_question(message, state):
        return

    await state.update_data(internet_speed=message.text.strip())

    await message.answer(
        "When would you be ready to start?\n\n"
        "We can schedule your interview and start training the same day!"
    )
    await state.set_state(OperatorForm.waiting_start_date)


# ═══ STEP 10: Start Date ═══

@router.message(OperatorForm.waiting_start_date)
async def process_start_date(message: Message, state: FSMContext):
    if await _handle_possible_question(message, state):
        return

    await state.update_data(start_date=message.text.strip())

    await message.answer(
        "Last question! 🙂\n\n"
        "Please share your contact for the interview:\n"
        "• Telegram @username (preferred)\n"
        "• Or WhatsApp number"
    )
    await state.set_state(OperatorForm.waiting_contact)


# ═══ STEP 11: Contact → Screening ═══

@router.message(OperatorForm.waiting_contact)
async def process_contact(message: Message, state: FSMContext):
    if await _handle_possible_question(message, state):
        return

    await state.update_data(contact_info=message.text.strip())
    data = await state.get_data()
    await state.clear()

    # Hardware decline
    if data.get("hardware_compatible") is False:
        await message.answer(DECLINE_HARDWARE)
        await _save_candidate(message, data, status="declined", notes="hardware incompatible")
        await _notify_admin(message, data, None, declined_reason="hardware")
        return

    # AI screening
    await message.answer(
        "Thank you for completing the application! 🎉\n\n"
        "I'm reviewing your information now — this usually takes about 30 seconds..."
    )

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

    await message.answer(result.suggested_response)

    # Save to DB
    await _save_candidate(
        message, data,
        status="screened",
        score=result.overall_score,
        recommendation=result.recommendation,
        notes=result.reasoning,
    )

    await _notify_admin(message, data, result)
    await _send_to_n8n(message, data, result)


# ═══ DB SAVE ═══

async def _save_candidate(
    message: Message,
    data: dict,
    status: str = "new",
    score=None,
    recommendation=None,
    notes=None,
    user=None,
):
    """Save candidate to the database."""
    from_user = user or message.from_user
    try:
        async with async_session() as session:
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

async def _notify_admin(
    message: Message,
    data: dict,
    result,
    declined_reason=None,
):
    if declined_reason:
        admin_text = (
            f"[OPERATOR — AUTO-DECLINED: {declined_reason.upper()}]\n\n"
            f"Name: {data.get('name', 'N/A')}\n"
            f"TG: @{message.from_user.username or 'N/A'} (ID: {message.from_user.id})\n"
            f"Age: {data.get('age', 'N/A')}\n"
            f"PC: {data.get('has_pc', 'N/A')} | Study: {data.get('study_status', 'N/A')}\n"
            f"CPU: {data.get('cpu_model', 'N/A')}\n"
            f"GPU: {data.get('gpu_model', 'N/A')}\n"
            f"Issues: {data.get('hardware_issues', 'N/A')}"
        )
        keyboard = None
    else:
        icon = {"PASS": "🟢", "MAYBE": "🟡", "REJECT": "🔴"}.get(result.recommendation, "❓")
        admin_text = (
            f"[OPERATOR] {icon} {result.recommendation} — Score: {result.overall_score}/100\n\n"
            f"Name: {data.get('name', 'N/A')}\n"
            f"TG: @{message.from_user.username or 'N/A'} (ID: {message.from_user.id})\n"
            f"Age: {data.get('age', 'N/A')} | English: {data.get('english_level', 'N/A')}\n"
            f"Study/Work: {data.get('study_status', 'N/A')}\n"
            f"CPU: {data.get('cpu_model', 'N/A')} | GPU: {data.get('gpu_model', 'N/A')}\n"
            f"HW Compatible: {'✅' if data.get('hardware_compatible') else '❌'}\n"
            f"Internet: {data.get('internet_speed', 'N/A')}\n"
            f"Start: {data.get('start_date', 'N/A')}\n"
            f"Contact: {data.get('contact_info', 'N/A')}\n\n"
            f"Scores: HW={result.hardware_score} | Eng={result.english_score} | "
            f"Avail={result.availability_score} | Motiv={result.motivation_score} | "
            f"Exp={result.experience_score}\n\n"
            f"Reasoning: {result.reasoning}"
        )
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [
                InlineKeyboardButton(text="✅ Send Interview Invite", callback_data=f"ref_{message.from_user.id}"),
                InlineKeyboardButton(text="❌ Reject", callback_data=f"rej_{message.from_user.id}"),
            ],
        ])

    try:
        await message.bot.send_message(config.ADMIN_CHAT_ID, admin_text, reply_markup=keyboard)
    except Exception:
        logger.exception("Failed to notify admin")


# ═══ N8N WEBHOOK ═══

async def _send_to_n8n(message: Message, data: dict, result):
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
