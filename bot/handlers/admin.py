"""Admin commands — only available to the configured ADMIN_CHAT_ID."""

import logging

from aiogram import F, Router
from aiogram.filters import Command
from aiogram.types import CallbackQuery, Message
from sqlalchemy import func, select

from bot.config import config
from bot.database import Candidate, async_session
from bot.services.post_generator import generate_post

logger = logging.getLogger(__name__)
router = Router()


def is_admin(message: Message) -> bool:
    return message.from_user.id == config.ADMIN_CHAT_ID


# --- Generate job post ---

@router.message(Command("post"), F.func(is_admin))
async def cmd_post(message: Message):
    """Usage: /post ph | /post ng | /post latam"""
    args = message.text.split(maxsplit=1)
    region = args[1].strip().lower() if len(args) > 1 else "ph"

    if region not in ("ph", "ng", "latam"):
        await message.answer("Usage: /post ph | /post ng | /post latam")
        return

    await message.answer(f"Generating post for {region.upper()}...")
    post_text = await generate_post(region)
    await message.answer(post_text)


# --- Screen a candidate from text ---

@router.message(Command("screen"), F.func(is_admin))
async def cmd_screen(message: Message):
    """Usage: /screen <candidate message text>"""
    args = message.text.split(maxsplit=1)
    if len(args) < 2:
        await message.answer("Usage: /screen <paste candidate's application text>")
        return

    from bot.services.screener import screen_candidate

    await message.answer("Screening...")
    result = await screen_candidate(name="Manual Screen", tg_username="admin_manual")
    await message.answer(
        f"Score: {result.overall_score}/100\n"
        f"Recommendation: {result.recommendation}\n\n"
        f"Hardware: {result.hardware_score} | English: {result.english_score}\n"
        f"Availability: {result.availability_score} | Motivation: {result.motivation_score}\n"
        f"Experience: {result.experience_score}\n\n"
        f"Reasoning: {result.reasoning}\n\n"
        f"Suggested response:\n{result.suggested_response}"
    )


# --- Pipeline / Stats ---

@router.message(Command("pipeline"), F.func(is_admin))
async def cmd_pipeline(message: Message):
    """Show candidate pipeline by status."""
    async with async_session() as session:
        result = await session.execute(
            select(Candidate.status, func.count(Candidate.id))
            .group_by(Candidate.status)
        )
        rows = result.all()

    if not rows:
        await message.answer("Pipeline is empty. No candidates yet.")
        return

    status_order = ["new", "screened", "interview_invited", "active", "churned"]
    status_map = dict(rows)
    lines = []
    total = 0
    for s in status_order:
        count = status_map.get(s, 0)
        total += count
        bar = "█" * count + "░" * max(0, 10 - count)
        lines.append(f"{s:>20}: {bar} {count}")

    text = f"Pipeline ({total} total):\n\n" + "\n".join(lines)
    await message.answer(f"```\n{text}\n```", parse_mode="Markdown")


@router.message(Command("stats"), F.func(is_admin))
async def cmd_stats(message: Message):
    """Quick earnings estimate."""
    async with async_session() as session:
        result = await session.execute(
            select(func.count(Candidate.id))
            .where(Candidate.status == "active")
            .where(Candidate.candidate_type == "operator")
        )
        active_operators = result.scalar() or 0

    # Progressive payout calculation
    payout = 0
    for i in range(1, active_operators + 1):
        if i <= 3:
            payout += 50
        elif i <= 6:
            payout += 75
        else:
            payout += 100

    await message.answer(
        f"Active operators: {active_operators}\n"
        f"Estimated payout: ${payout}\n\n"
        f"Referral link: {config.REFERRAL_LINK or 'Not set — update .env'}"
    )


# --- Referral link ---

@router.message(Command("ref"), F.func(is_admin))
async def cmd_ref(message: Message):
    """Show referral link."""
    link = config.REFERRAL_LINK or "Not configured — set REFERRAL_LINK in .env"
    await message.answer(f"Your referral link:\n{link}")


# --- Callback: send referral link to candidate ---

@router.callback_query(F.data.startswith("ref_"))
async def cb_send_referral(callback: CallbackQuery):
    user_id = int(callback.data.removeprefix("ref_"))
    link = config.REFERRAL_LINK or "https://t.me/huntme_webinar_bot"
    try:
        await callback.bot.send_message(
            user_id,
            "Great news! You've been selected for an interview! 🎉\n\n"
            "Please register through the link below to choose your interview time:\n"
            f"{link}\n\n"
            "The interview is a quick 15-minute Zoom call where we'll:\n"
            "• Explain the role in detail\n"
            "• Answer all your questions\n"
            "• Do a quick age verification\n\n"
            "Looking forward to meeting you! 🙂",
        )
        await callback.answer("Interview invite sent!")
        await callback.message.edit_text(callback.message.text + "\n\n✅ INTERVIEW INVITE SENT")
    except Exception:
        await callback.answer("Failed to send — user may have blocked the bot")


@router.callback_query(F.data.startswith("rej_"))
async def cb_reject(callback: CallbackQuery):
    user_id = int(callback.data.removeprefix("rej_"))
    try:
        await callback.bot.send_message(
            user_id,
            "Thank you for your interest in our team! 🙏\n\n"
            "Unfortunately, we're not able to move forward with your application "
            "at this time. We'll keep your information on file for future openings.\n\n"
            "If you know anyone who might be interested in a remote moderator position, "
            "feel free to send them our way!\n\n"
            "Wishing you all the best! 🙂",
        )
        await callback.answer("Rejection sent.")
        await callback.message.edit_text(callback.message.text + "\n\n❌ REJECTED")
    except Exception:
        await callback.answer("Failed to send")


# --- Agent callbacks ---

@router.callback_query(F.data.startswith("agentok_"))
async def cb_approve_agent(callback: CallbackQuery):
    user_id = int(callback.data.removeprefix("agentok_"))
    try:
        await callback.bot.send_message(
            user_id,
            "Great news — you've been approved as a Recruitment Agent! 🎉\n\n"
            "Here's what happens next:\n"
            "• You'll receive your unique referral link\n"
            "• Share it with potential operators and models\n"
            "• Earn $50-100 per operator + $10/day per model for 12 months\n"
            "• Payouts every Sunday in USDT (BEP20), minimum $50\n\n"
            "Our team will be in touch shortly with your onboarding details.\n\n"
            "Welcome to the team! 🙂",
        )
        await callback.answer("Agent approved!")
        await callback.message.edit_text(callback.message.text + "\n\n✅ AGENT APPROVED")
    except Exception:
        await callback.answer("Failed to send — user may have blocked the bot")


@router.callback_query(F.data.startswith("agentno_"))
async def cb_reject_agent(callback: CallbackQuery):
    user_id = int(callback.data.removeprefix("agentno_"))
    try:
        await callback.bot.send_message(
            user_id,
            "Thank you for your interest in our Agent program! 🙏\n\n"
            "Unfortunately, we're not able to move forward with your application "
            "at this time.\n\n"
            "If your situation changes or you'd like to apply for another role, "
            "feel free to reach out again — just send /start.\n\n"
            "Wishing you all the best! 🙂",
        )
        await callback.answer("Rejection sent.")
        await callback.message.edit_text(callback.message.text + "\n\n❌ REJECTED")
    except Exception:
        await callback.answer("Failed to send")


# --- Model callbacks ---

@router.callback_query(F.data.startswith("modelok_"))
async def cb_approve_model(callback: CallbackQuery):
    user_id = int(callback.data.removeprefix("modelok_"))
    try:
        await callback.bot.send_message(
            user_id,
            "Great news — you've been approved as a Content Creator! 🎉\n\n"
            "Here's what happens next:\n"
            "• You'll be paired with a dedicated operator\n"
            "• You'll go through 5-7 days of paid training ($30/shift)\n"
            "• Your first paycheck comes at the end of your first training week\n"
            "• Payments every Sunday via GCash / Wise / USDT\n\n"
            "Our team will be in touch shortly to get you started.\n\n"
            "Welcome to the team! 🙂",
        )
        await callback.answer("Model approved!")
        await callback.message.edit_text(callback.message.text + "\n\n✅ MODEL APPROVED")
    except Exception:
        await callback.answer("Failed to send — user may have blocked the bot")


@router.callback_query(F.data.startswith("modelno_"))
async def cb_reject_model(callback: CallbackQuery):
    user_id = int(callback.data.removeprefix("modelno_"))
    try:
        await callback.bot.send_message(
            user_id,
            "Thank you for your interest in joining our team! 🙏\n\n"
            "Unfortunately, we're not able to move forward with your application "
            "at this time.\n\n"
            "If your situation changes or you'd like to explore other roles, "
            "feel free to reach out again — just send /start.\n\n"
            "Wishing you all the best! 🙂",
        )
        await callback.answer("Rejection sent.")
        await callback.message.edit_text(callback.message.text + "\n\n❌ REJECTED")
    except Exception:
        await callback.answer("Failed to send")


# --- Help ---

@router.message(Command("help"), F.func(is_admin))
async def cmd_help(message: Message):
    await message.answer(
        "Admin commands:\n\n"
        "/post [ph|ng|latam] — Generate a job posting\n"
        "/screen <text> — Screen a candidate's application\n"
        "/pipeline — View candidate funnel\n"
        "/stats — Earnings estimate\n"
        "/ref — Show referral link\n"
        "/help — This message"
    )
