"""Admin commands — only available to the configured ADMIN_CHAT_ID.

Features:
- /post, /pipeline, /stats, /ref, /help commands
- Approve/reject callbacks for operators
- Reply-to-message handler for answering candidate questions
"""

import logging
import re

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


# ═══ REPLY TO CANDIDATE QUESTIONS ═══

@router.message(F.reply_to_message, F.func(is_admin))
async def admin_reply_to_candidate(message: Message):
    """Admin replies to a forwarded question → send answer to candidate."""
    replied = message.reply_to_message
    if not replied or not replied.text:
        return

    # Only handle replies to question-forwarding messages
    if "❓ QUESTION from" not in replied.text:
        return

    # Extract user ID from the forwarded message
    match = re.search(r"ID:\s*(\d+)", replied.text)
    if not match:
        return

    user_id = int(match.group(1))
    try:
        await message.bot.send_message(
            user_id,
            f"Reply from our team:\n\n{message.text}",
        )
        await message.answer("✅ Answer sent to candidate.")
    except Exception:
        await message.answer("❌ Failed to send — candidate may have blocked the bot.")


# ═══ GENERATE JOB POST ═══

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


# ═══ SCREEN CANDIDATE FROM TEXT ═══

@router.message(Command("screen"), F.func(is_admin))
async def cmd_screen(message: Message):
    """Usage: /screen <paste candidate's application text>"""
    args = message.text.split(maxsplit=1)
    if len(args) < 2:
        await message.answer("Usage: /screen <paste candidate's application text>")
        return

    candidate_text = args[1].strip()

    from bot.services.screener import screen_candidate

    await message.answer("Screening...")
    result = await screen_candidate(
        name="Manual Screen",
        tg_username="admin_manual",
        pc_confidence=candidate_text,
    )
    await message.answer(
        f"Score: {result.overall_score}/100\n"
        f"Recommendation: {result.recommendation}\n\n"
        f"Hardware: {result.hardware_score} | English: {result.english_score}\n"
        f"Availability: {result.availability_score} | Motivation: {result.motivation_score}\n"
        f"Experience: {result.experience_score}\n\n"
        f"Reasoning: {result.reasoning}\n\n"
        f"Suggested response:\n{result.suggested_response}"
    )


# ═══ PIPELINE / STATS ═══

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

    status_order = ["new", "screened", "interview_invited", "active", "declined", "churned"]
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


# ═══ REFERRAL LINK ═══

@router.message(Command("ref"), F.func(is_admin))
async def cmd_ref(message: Message):
    """Show referral link."""
    link = config.REFERRAL_LINK or "Not configured — set REFERRAL_LINK in .env"
    await message.answer(f"Your referral link:\n{link}")


# ═══ OPERATOR CALLBACKS ═══

@router.callback_query(F.data.startswith("ref_"))
async def cb_send_referral(callback: CallbackQuery):
    """Send interview invite to candidate + update DB status."""
    user_id = int(callback.data.removeprefix("ref_"))
    link = config.REFERRAL_LINK or "https://t.me/huntme_webinar_bot"
    try:
        await callback.bot.send_message(
            user_id,
            "Great news! You've been selected for an interview! 🎉\n\n"
            "Please register through the link below to choose your interview time:\n"
            f"{link}\n\n"
            "The interview is a 30-40 minute video call where we'll:\n"
            "• Explain the role in detail\n"
            "• Answer all your questions\n"
            "• Do a quick age verification\n\n"
            "Looking forward to meeting you! 🙂",
        )
        # Update status in DB
        try:
            async with async_session() as session:
                result = await session.execute(
                    select(Candidate).where(Candidate.tg_user_id == user_id)
                )
                candidate = result.scalar_one_or_none()
                if candidate:
                    candidate.status = "interview_invited"
                    await session.commit()
        except Exception:
            logger.debug("Failed to update candidate status")

        await callback.answer("Interview invite sent!")
        await callback.message.edit_text(callback.message.text + "\n\n✅ INTERVIEW INVITE SENT")
    except Exception:
        await callback.answer("Failed to send — user may have blocked the bot")


@router.callback_query(F.data.startswith("rej_"))
async def cb_reject(callback: CallbackQuery):
    """Send rejection to candidate + update DB status."""
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
        # Update status in DB
        try:
            async with async_session() as session:
                result = await session.execute(
                    select(Candidate).where(Candidate.tg_user_id == user_id)
                )
                candidate = result.scalar_one_or_none()
                if candidate:
                    candidate.status = "declined"
                    await session.commit()
        except Exception:
            logger.debug("Failed to update candidate status")

        await callback.answer("Rejection sent.")
        await callback.message.edit_text(callback.message.text + "\n\n❌ REJECTED")
    except Exception:
        await callback.answer("Failed to send")


# ═══ HELP ═══

@router.message(Command("help"), F.func(is_admin))
async def cmd_help(message: Message):
    await message.answer(
        "Admin commands:\n\n"
        "/post [ph|ng|latam] — Generate a job posting\n"
        "/screen <text> — Screen a candidate's application\n"
        "/pipeline — View candidate funnel\n"
        "/stats — Earnings estimate\n"
        "/ref — Show referral link\n"
        "/help — This message\n\n"
        "To answer candidate questions:\n"
        "Reply to any ❓ QUESTION message to send your answer directly to the candidate."
    )
