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
    result = await screen_candidate(name="Unknown", message=args[1])
    await message.answer(
        f"Score: {result.overall_score}/100\n"
        f"Recommendation: {result.recommendation}\n\n"
        f"English: {result.english_score} | Experience: {result.experience_score}\n"
        f"Availability: {result.availability_score} | Equipment: {result.equipment_score}\n"
        f"Motivation: {result.motivation_score}\n\n"
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

    status_order = ["new", "screened", "link_sent", "webinar_registered", "active", "churned"]
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
            f"Great news! You've been selected for the next step.\n\n"
            f"Please register for our onboarding webinar here:\n{link}\n\n"
            f"Pick a time that works for you. See you there!",
        )
        await callback.answer("Referral link sent!")
        await callback.message.edit_text(callback.message.text + "\n\n--- REFERRAL SENT ---")
    except Exception:
        await callback.answer("Failed to send — user may have blocked the bot")


@router.callback_query(F.data.startswith("rej_"))
async def cb_reject(callback: CallbackQuery):
    user_id = int(callback.data.removeprefix("rej_"))
    try:
        await callback.bot.send_message(
            user_id,
            "Thank you for your interest! Unfortunately, we don't have a matching "
            "position right now. We'll keep your application on file for future openings. "
            "Best of luck!",
        )
        await callback.answer("Rejection sent.")
        await callback.message.edit_text(callback.message.text + "\n\n--- REJECTED ---")
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
