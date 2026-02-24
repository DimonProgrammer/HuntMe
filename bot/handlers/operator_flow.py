"""11-step FSM flow for operator (Live Stream Moderator) qualification.

Extracted from candidate.py. Triggered from menu.py when user selects Operator.
Steps: name → PC → age → study/work → english → PC confidence →
       CPU → GPU → internet → start date → contact
"""

import logging

import aiohttp
from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup, Message

from bot.config import config
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


# --- Step 1: Name ---

@router.message(OperatorForm.waiting_name)
async def process_name(message: Message, state: FSMContext):
    name = message.text.strip()

    objection = detect_objection(name)
    if objection and len(name) > 30:
        response = get_response(objection)
        if response:
            await message.answer(response)
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
        "Nice to meet you, {}! 🙂\n\n"
        "Do you have a personal PC or laptop? (Windows only — MacBooks are not supported)".format(name.split()[0]),
        reply_markup=keyboard,
    )
    await state.set_state(OperatorForm.waiting_has_pc)


# --- Step 2: PC Check ---

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


# --- Step 3: Age ---

@router.message(OperatorForm.waiting_age)
async def process_age(message: Message, state: FSMContext):
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


# --- Step 4: Study/Work Status ---

@router.callback_query(OperatorForm.waiting_study_work, F.data.startswith("study_"))
async def process_study_work(callback: CallbackQuery, state: FSMContext):
    status = callback.data.removeprefix("study_")
    await callback.answer()

    if status == "inperson":
        await state.update_data(study_status="student_inperson")
        await callback.message.answer(DECLINE_STUDENT_INPERSON)
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


# --- Step 5: English Level ---

@router.callback_query(OperatorForm.waiting_english, F.data.startswith("eng_"))
async def process_english(callback: CallbackQuery, state: FSMContext):
    level = callback.data.removeprefix("eng_")
    await callback.answer()

    if level == "beginner":
        await state.update_data(english_level="beginner")
        await callback.message.answer(DECLINE_ENGLISH)
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


# --- Step 6: PC Confidence ---

@router.message(OperatorForm.waiting_pc_confidence)
async def process_pc_confidence(message: Message, state: FSMContext):
    await state.update_data(pc_confidence=message.text.strip())

    await message.answer(
        "What is your processor (CPU) model?\n\n"
        "How to check: Press Win+R → type 'dxdiag' → press Enter → "
        "look at 'Processor' line\n\n"
        "Example: Intel Core i5-12400 or AMD Ryzen 5 5600"
    )
    await state.set_state(OperatorForm.waiting_cpu)


# --- Step 7: CPU ---

@router.message(OperatorForm.waiting_cpu)
async def process_cpu(message: Message, state: FSMContext):
    cpu = message.text.strip()

    objection = detect_objection(cpu)
    if objection and len(cpu) > 20:
        response = get_response(objection)
        if response:
            await message.answer(response)
            await message.answer(
                "Now, back to the application — "
                "what is your processor model? 🙂\n\n"
                "Press Win+R → type 'dxdiag' → Enter → look at 'Processor'"
            )
            return

    await state.update_data(cpu_model=cpu)

    await message.answer(
        "What is your graphics card (GPU)?\n\n"
        "In the same dxdiag window → click 'Display' tab → "
        "look at 'Name' under Device\n\n"
        "Example: NVIDIA GeForce RTX 3060 or AMD Radeon RX 6600"
    )
    await state.set_state(OperatorForm.waiting_gpu)


# --- Step 8: GPU ---

@router.message(OperatorForm.waiting_gpu)
async def process_gpu(message: Message, state: FSMContext):
    gpu = message.text.strip()
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


# --- Step 9: Internet Speed ---

@router.message(OperatorForm.waiting_internet)
async def process_internet(message: Message, state: FSMContext):
    await state.update_data(internet_speed=message.text.strip())

    await message.answer(
        "When would you be ready to start?\n\n"
        "Our next training group starts soon — ideally within 1 week."
    )
    await state.set_state(OperatorForm.waiting_start_date)


# --- Step 10: Start Date ---

@router.message(OperatorForm.waiting_start_date)
async def process_start_date(message: Message, state: FSMContext):
    await state.update_data(start_date=message.text.strip())

    await message.answer(
        "Last question! 🙂\n\n"
        "Please share your contact for the interview:\n"
        "• Telegram @username (preferred)\n"
        "• Or WhatsApp number"
    )
    await state.set_state(OperatorForm.waiting_contact)


# --- Step 11: Contact → Screening ---

@router.message(OperatorForm.waiting_contact)
async def process_contact(message: Message, state: FSMContext):
    await state.update_data(contact_info=message.text.strip())
    data = await state.get_data()
    await state.clear()

    if data.get("hardware_compatible") is False:
        await message.answer(DECLINE_HARDWARE)
        await _notify_admin(message, data, None, declined_reason="hardware")
        return

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
    await _notify_admin(message, data, result)
    await _send_to_n8n(message, data, result)


async def _notify_admin(
    message: Message,
    data: dict,
    result,
    declined_reason: str | None = None,
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


async def _send_to_n8n(message: Message, data: dict, result):
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
