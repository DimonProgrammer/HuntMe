"""Main menu handler — /start, role selection, info pages, company info."""

import logging

from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup, Message

from bot.config import config
from bot.handlers.operator_flow import OperatorForm
from bot.handlers.agent_flow import AgentForm
from bot.handlers.model_flow import ModelForm

logger = logging.getLogger(__name__)
router = Router()


class MenuStates(StatesGroup):
    main_menu = State()
    role_select = State()
    info_select = State()


# --- Keyboards ---

def _main_menu_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Apply Now", callback_data="menu_apply")],
        [InlineKeyboardButton(text="About Our Vacancies", callback_data="menu_vacancies")],
        [InlineKeyboardButton(text="About the Company", callback_data="menu_company")],
    ])


def _back_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="<< Back to Menu", callback_data="back_main")],
    ])


# --- Main menu text ---

MAIN_MENU_TEXT = (
    "Welcome to Apex Talent! 👋\n\n"
    "We're an international talent management agency working with "
    "content creators on streaming platforms in 15+ countries.\n\n"
    "What would you like to do?"
)


# --- /start ---

@router.message(F.text == "/start")
async def cmd_start(message: Message, state: FSMContext):
    if message.from_user.id == config.ADMIN_CHAT_ID:
        return
    await state.clear()
    await message.answer(MAIN_MENU_TEXT, reply_markup=_main_menu_kb())
    await state.set_state(MenuStates.main_menu)


# --- /menu — return from anywhere ---

@router.message(F.text == "/menu")
async def cmd_menu(message: Message, state: FSMContext):
    if message.from_user.id == config.ADMIN_CHAT_ID:
        return
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


# --- Apply Now → role selection ---

@router.callback_query(MenuStates.main_menu, F.data == "menu_apply")
async def cb_menu_apply(callback: CallbackQuery, state: FSMContext):
    await callback.answer()
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Live Stream Operator", callback_data="role_operator")],
        [InlineKeyboardButton(text="Recruitment Agent", callback_data="role_agent")],
        [InlineKeyboardButton(text="Content Creator / Model", callback_data="role_model")],
        [InlineKeyboardButton(text="<< Back to Menu", callback_data="back_main")],
    ])
    text = (
        "Which role are you interested in?\n\n"
        "Live Stream Operator — technical setup, chat moderation, $150-400+/wk\n\n"
        "Recruitment Agent — refer talent, earn $50-100 per hire + passive income\n\n"
        "Content Creator — stream on platforms, flexible hours, revenue share"
    )
    try:
        await callback.message.edit_text(text, reply_markup=keyboard)
    except Exception:
        await callback.message.answer(text, reply_markup=keyboard)
    await state.set_state(MenuStates.role_select)


# --- Role selection → hand off to flow ---

@router.callback_query(MenuStates.role_select, F.data == "role_operator")
async def cb_role_operator(callback: CallbackQuery, state: FSMContext):
    await callback.answer()
    await state.update_data(candidate_type="operator")
    from bot.services.followup import WARM_GREETING
    greeting = WARM_GREETING.format(name=callback.from_user.first_name or "there")
    try:
        await callback.message.edit_text(greeting)
    except Exception:
        await callback.message.answer(greeting)
    await state.set_state(OperatorForm.waiting_name)


@router.callback_query(MenuStates.role_select, F.data == "role_agent")
async def cb_role_agent(callback: CallbackQuery, state: FSMContext):
    await callback.answer()
    await state.update_data(candidate_type="agent")
    from bot.services.followup import AGENT_GREETING
    greeting = AGENT_GREETING.format(name=callback.from_user.first_name or "there")
    try:
        await callback.message.edit_text(greeting)
    except Exception:
        await callback.message.answer(greeting)
    await state.set_state(AgentForm.waiting_name)


@router.callback_query(MenuStates.role_select, F.data == "role_model")
async def cb_role_model(callback: CallbackQuery, state: FSMContext):
    await callback.answer()
    await state.update_data(candidate_type="model")
    from bot.services.followup import MODEL_GREETING
    greeting = MODEL_GREETING.format(name=callback.from_user.first_name or "there")
    try:
        await callback.message.edit_text(greeting)
    except Exception:
        await callback.message.answer(greeting)
    await state.set_state(ModelForm.waiting_name)


# --- About Vacancies ---

@router.callback_query(MenuStates.main_menu, F.data == "menu_vacancies")
async def cb_menu_vacancies(callback: CallbackQuery, state: FSMContext):
    await callback.answer()
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Live Stream Operator", callback_data="info_operator")],
        [InlineKeyboardButton(text="Recruitment Agent", callback_data="info_agent")],
        [InlineKeyboardButton(text="Content Creator / Model", callback_data="info_model")],
        [InlineKeyboardButton(text="<< Back to Menu", callback_data="back_main")],
    ])
    try:
        await callback.message.edit_text(
            "Which role would you like to learn about?",
            reply_markup=keyboard,
        )
    except Exception:
        await callback.message.answer(
            "Which role would you like to learn about?",
            reply_markup=keyboard,
        )
    await state.set_state(MenuStates.info_select)


@router.callback_query(MenuStates.info_select, F.data == "info_operator")
async def cb_info_operator(callback: CallbackQuery, state: FSMContext):
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
        "  • Starting: $150/week ($600/month)\n"
        "  • After 1-2 months: $200-300/week\n"
        "  • Top performers: $400+/week\n"
        "  • Paid training: 5-7 days, $30 per shift\n\n"
        "Schedule:\n"
        "  • 5 days/week, 2 days off\n"
        "  • 6-8 hours/day\n"
        "  • 4 shift options: morning / day / evening / night\n"
        "  • Payment every Sunday (GCash / Wise / USDT)\n\n"
        "Requirements:\n"
        "  • Windows PC or laptop (MacBooks not supported)\n"
        "  • CPU: Intel Core i3 10th gen+ or AMD Ryzen 3 3000+\n"
        "  • GPU: NVIDIA GTX 1060 6GB+ or AMD RX 5500+\n"
        "  • Internet: 100 Mbps+\n"
        "  • English: B1 (Intermediate) minimum\n"
        "  • Age: 18+"
    )
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Apply as Operator", callback_data="apply_from_info_operator")],
        [InlineKeyboardButton(text="<< Back", callback_data="back_vacancies")],
    ])
    try:
        await callback.message.edit_text(text, reply_markup=keyboard)
    except Exception:
        await callback.message.answer(text, reply_markup=keyboard)


@router.callback_query(MenuStates.info_select, F.data == "info_agent")
async def cb_info_agent(callback: CallbackQuery, state: FSMContext):
    await callback.answer()
    text = (
        "RECRUITMENT AGENT\n\n"
        "What you'll do:\n"
        "  • Find and refer talented operators and models\n"
        "  • Earn commissions for every successful hire\n"
        "  • Work at your own pace — no fixed schedule\n\n"
        "Earnings per Operator referred:\n"
        "  • 1st–3rd hire: $50 each\n"
        "  • 4th–6th hire: $75 each\n"
        "  • 7th+ hire: $100 each\n\n"
        "Earnings per Model referred:\n"
        "  • $10 per working day for 12 months (passive income!)\n\n"
        "Payment:\n"
        "  • USDT (BEP20 network)\n"
        "  • Every Sunday\n"
        "  • $50 minimum payout\n\n"
        "Requirements:\n"
        "  • English B1+\n"
        "  • Access to social media / job platforms / local networks\n"
        "  • Self-motivated and proactive"
    )
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Apply as Agent", callback_data="apply_from_info_agent")],
        [InlineKeyboardButton(text="<< Back", callback_data="back_vacancies")],
    ])
    try:
        await callback.message.edit_text(text, reply_markup=keyboard)
    except Exception:
        await callback.message.answer(text, reply_markup=keyboard)


@router.callback_query(MenuStates.info_select, F.data == "info_model")
async def cb_info_model(callback: CallbackQuery, state: FSMContext):
    await callback.answer()
    text = (
        "CONTENT CREATOR / MODEL\n\n"
        "What you'll do:\n"
        "  • Create content on streaming platforms\n"
        "  • Work with a dedicated operator who handles all tech\n"
        "  • Build your audience and grow your income over time\n\n"
        "What we provide:\n"
        "  • Full training with a personal mentor\n"
        "  • Technical support from your operator\n"
        "  • Revenue share — the more you grow, the more you earn\n"
        "  • Weekly payments (GCash / Wise / USDT)\n\n"
        "Schedule:\n"
        "  • Flexible — you choose your hours\n"
        "  • 4 shift options available\n"
        "  • 100% work from home\n\n"
        "Requirements:\n"
        "  • Age: 18+\n"
        "  • Comfortable being on camera\n"
        "  • Reliable internet connection"
    )
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Apply as Model", callback_data="apply_from_info_model")],
        [InlineKeyboardButton(text="<< Back", callback_data="back_vacancies")],
    ])
    try:
        await callback.message.edit_text(text, reply_markup=keyboard)
    except Exception:
        await callback.message.answer(text, reply_markup=keyboard)


# --- Apply shortcuts from info pages ---

@router.callback_query(F.data == "apply_from_info_operator")
async def cb_apply_from_info_operator(callback: CallbackQuery, state: FSMContext):
    await callback.answer()
    await state.update_data(candidate_type="operator")
    from bot.services.followup import WARM_GREETING
    greeting = WARM_GREETING.format(name=callback.from_user.first_name or "there")
    try:
        await callback.message.edit_text(greeting)
    except Exception:
        await callback.message.answer(greeting)
    await state.set_state(OperatorForm.waiting_name)


@router.callback_query(F.data == "apply_from_info_agent")
async def cb_apply_from_info_agent(callback: CallbackQuery, state: FSMContext):
    await callback.answer()
    await state.update_data(candidate_type="agent")
    from bot.services.followup import AGENT_GREETING
    greeting = AGENT_GREETING.format(name=callback.from_user.first_name or "there")
    try:
        await callback.message.edit_text(greeting)
    except Exception:
        await callback.message.answer(greeting)
    await state.set_state(AgentForm.waiting_name)


@router.callback_query(F.data == "apply_from_info_model")
async def cb_apply_from_info_model(callback: CallbackQuery, state: FSMContext):
    await callback.answer()
    await state.update_data(candidate_type="model")
    from bot.services.followup import MODEL_GREETING
    greeting = MODEL_GREETING.format(name=callback.from_user.first_name or "there")
    try:
        await callback.message.edit_text(greeting)
    except Exception:
        await callback.message.answer(greeting)
    await state.set_state(ModelForm.waiting_name)


# --- Back to vacancies list ---

@router.callback_query(F.data == "back_vacancies")
async def cb_back_vacancies(callback: CallbackQuery, state: FSMContext):
    await callback.answer()
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Live Stream Operator", callback_data="info_operator")],
        [InlineKeyboardButton(text="Recruitment Agent", callback_data="info_agent")],
        [InlineKeyboardButton(text="Content Creator / Model", callback_data="info_model")],
        [InlineKeyboardButton(text="<< Back to Menu", callback_data="back_main")],
    ])
    try:
        await callback.message.edit_text(
            "Which role would you like to learn about?",
            reply_markup=keyboard,
        )
    except Exception:
        await callback.message.answer(
            "Which role would you like to learn about?",
            reply_markup=keyboard,
        )
    await state.set_state(MenuStates.info_select)


# --- About Company ---

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
        "  • Weekly payments every Sunday, without exception\n"
        "  • Dedicated mentor for every new team member\n\n"
        "Open roles:\n"
        "  • Live Stream Operators (technical, behind-the-scenes)\n"
        "  • Content Creators (streaming on platforms)\n"
        "  • Recruitment Agents (refer talent, earn commissions)\n\n"
        "We never ask for upfront payments.\n"
        "Your first earnings start during paid training ($30/shift, 5-7 days)."
    )
    try:
        await callback.message.edit_text(text, reply_markup=_back_kb())
    except Exception:
        await callback.message.answer(text, reply_markup=_back_kb())
