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
from aiogram.types import CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup, Message
from sqlalchemy import func, select

from bot.config import config
from bot.database import Candidate, FunnelEvent, async_session
from bot.messages import msg
from bot.services.post_generator import generate_post

logger = logging.getLogger(__name__)
router = Router()


def is_admin(message: Message) -> bool:
    return message.from_user.id == config.ADMIN_CHAT_ID


# ═══ REPLY TO CANDIDATE QUESTIONS ═══

@router.message(F.reply_to_message, F.func(is_admin))
async def admin_reply_to_candidate(message: Message):
    """Admin replies to any bot message containing a user ID → forward to candidate."""
    replied = message.reply_to_message
    if not replied or not replied.text:
        return

    # Extract user ID from any message format
    user_id = None
    match = re.search(r"(?:ID|candidate ID)[:\s]*(\d{5,})", replied.text)
    if match:
        user_id = int(match.group(1))

    if not user_id:
        return

    # Look up candidate for name + language
    candidate_name = None
    cand = None
    try:
        async with async_session() as session:
            result = await session.execute(
                select(Candidate).where(Candidate.tg_user_id == user_id)
            )
            cand = result.scalar_one_or_none()
            if cand:
                candidate_name = cand.name
    except Exception:
        pass

    cand_lang = cand.language if cand and cand.language else "en"
    m = msg(cand_lang)

    try:
        from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
        reply_kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text=m.BTN_CONTINUE, callback_data="resume_form")],
            [InlineKeyboardButton(text=m.BTN_QUESTION, callback_data="menu_question")],
            [InlineKeyboardButton(text=m.BTN_BACK_MENU, callback_data="back_main")],
        ])
        await message.bot.send_message(user_id, message.text, reply_markup=reply_kb)
        name_str = f" ({candidate_name})" if candidate_name else ""
        preview = message.text[:80] + ("..." if len(message.text) > 80 else "")
        await message.answer(
            f"✅ Delivered to {user_id}{name_str}\n"
            f"📝 \"{preview}\""
        )
    except Exception as e:
        error_str = str(e)
        if "blocked" in error_str.lower() or "deactivated" in error_str.lower():
            await message.answer(f"❌ Candidate {user_id} blocked the bot or deleted their account.")
        elif "not found" in error_str.lower():
            await message.answer(f"❌ User {user_id} not found — never started the bot.")
        else:
            await message.answer(f"❌ Failed to send to {user_id}: {error_str[:100]}")


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
    """Send interview booking button to candidate (MAYBE candidates approved by admin)."""
    user_id = int(callback.data.removeprefix("ref_"))
    # Get candidate language
    cand_lang = "en"
    cand = None
    try:
        async with async_session() as session:
            result = await session.execute(
                select(Candidate).where(Candidate.tg_user_id == user_id)
            )
            cand = result.scalar_one_or_none()
            if cand and cand.language:
                cand_lang = cand.language
    except Exception:
        pass
    m = msg(cand_lang)
    try:
        from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
        booking_kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="📅 Book Interview", callback_data="start_booking")],
        ])
        await callback.bot.send_message(
            user_id,
            m.BOOKING_START,
            reply_markup=booking_kb,
        )
        # Notify referrer if this candidate was referred
        try:
            async with async_session() as session:
                result = await session.execute(
                    select(Candidate).where(Candidate.tg_user_id == user_id)
                )
                cand = result.scalar_one_or_none()
                if cand and cand.referrer_tg_id:
                    await callback.bot.send_message(
                        cand.referrer_tg_id,
                        f"Great news! Your referral {cand.name.split()[0]} has been invited "
                        f"to an interview! 🎉\n\n"
                        "Keep referring — you earn $50-100 per hired person.\n"
                        "Your link: /referral",
                    )
        except Exception:
            logger.debug("Failed to notify referrer")

        await callback.answer("Booking invite sent!")
        await callback.message.edit_text(callback.message.text + "\n\n✅ BOOKING INVITE SENT")
    except Exception:
        await callback.answer("Failed to send — user may have blocked the bot")


@router.callback_query(F.data.startswith("rej_"))
async def cb_reject(callback: CallbackQuery):
    """Send rejection to candidate + update DB status."""
    user_id = int(callback.data.removeprefix("rej_"))
    # Get candidate language
    cand_lang = "en"
    try:
        async with async_session() as session:
            result = await session.execute(
                select(Candidate).where(Candidate.tg_user_id == user_id)
            )
            cand = result.scalar_one_or_none()
            if cand and cand.language:
                cand_lang = cand.language
    except Exception:
        pass
    m = msg(cand_lang)
    share_url = (
        "https://t.me/share/url?url=https://apextalent.pro/ru"
        if cand_lang == "ru"
        else "https://t.me/share/url?url=https://apextalent.pro"
    )
    share_kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=m.BTN_SHARE_REFERRAL, url=share_url)],
    ])
    try:
        await callback.bot.send_message(user_id, m.REJECTION_MESSAGE, reply_markup=share_kb)
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


# ═══ MESSAGE CANDIDATE (inline button) ═══

@router.callback_query(F.data.startswith("msg_"))
async def cb_message_candidate(callback: CallbackQuery):
    """Prompt admin to reply with a message for the candidate."""
    user_id = callback.data.removeprefix("msg_")
    await callback.answer()
    await callback.message.answer(
        f"Reply to THIS message with your text for candidate ID {user_id}.\n"
        "The message will be sent to them directly."
    )


# ═══ /msg — Send direct message to any candidate ═══

@router.message(Command("msg"), F.func(is_admin))
async def cmd_msg(message: Message):
    """Usage: /msg <user_id> <text>"""
    parts = message.text.split(maxsplit=2)
    if len(parts) < 3:
        await message.answer("Usage: /msg <user_id or @username> <text>")
        return

    target = parts[1].strip()
    text = parts[2].strip()

    # Resolve @username to user_id
    if target.startswith("@"):
        try:
            async with async_session() as session:
                result = await session.execute(
                    select(Candidate).where(Candidate.tg_username == target.lstrip("@"))
                )
                cand = result.scalar_one_or_none()
                if not cand:
                    await message.answer(f"Candidate {target} not found in DB.")
                    return
                user_id = cand.tg_user_id
        except Exception:
            await message.answer("DB error.")
            return
    else:
        try:
            user_id = int(target)
        except ValueError:
            await message.answer("Invalid user ID. Use a number or @username.")
            return

    # Look up name + language
    candidate_name = None
    cand = None
    try:
        async with async_session() as session:
            result = await session.execute(
                select(Candidate).where(Candidate.tg_user_id == user_id)
            )
            cand = result.scalar_one_or_none()
            if cand:
                candidate_name = cand.name
    except Exception:
        pass

    cand_lang = cand.language if cand and cand.language else "en"
    cm = msg(cand_lang)

    try:
        from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
        reply_kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text=cm.BTN_CONTINUE, callback_data="resume_form")],
            [InlineKeyboardButton(text=cm.BTN_QUESTION, callback_data="menu_question")],
            [InlineKeyboardButton(text=cm.BTN_BACK_MENU, callback_data="back_main")],
        ])
        await message.bot.send_message(user_id, text, reply_markup=reply_kb)
        name_str = f" ({candidate_name})" if candidate_name else ""
        preview = text[:80] + ("..." if len(text) > 80 else "")
        await message.answer(
            f"✅ Delivered to {user_id}{name_str}\n"
            f"📝 \"{preview}\""
        )
    except Exception as e:
        error_str = str(e)
        if "blocked" in error_str.lower() or "deactivated" in error_str.lower():
            await message.answer(f"❌ Candidate {user_id} blocked the bot.")
        else:
            await message.answer(f"❌ Failed: {error_str[:100]}")


# ═══ FUNNEL ANALYTICS ═══

@router.message(Command("funnel"), F.func(is_admin))
async def cmd_funnel(message: Message):
    """Show step-by-step funnel conversion analytics."""
    async with async_session() as session:
        # Count events by step_name for step_completed and declined
        result = await session.execute(
            select(FunnelEvent.event_type, FunnelEvent.step_name, func.count(FunnelEvent.id))
            .group_by(FunnelEvent.event_type, FunnelEvent.step_name)
            .order_by(func.count(FunnelEvent.id).desc())
        )
        rows = result.all()

        # Total unique users who started
        starts = await session.execute(
            select(func.count(func.distinct(FunnelEvent.tg_user_id)))
            .where(FunnelEvent.event_type == "bot_started")
        )
        total_starts = starts.scalar() or 0

        # Total unique users who clicked Apply
        applies = await session.execute(
            select(func.count(func.distinct(FunnelEvent.tg_user_id)))
            .where(FunnelEvent.event_type == "button_clicked")
            .where(FunnelEvent.step_name == "apply_now")
        )
        total_applies = applies.scalar() or 0

        # Completed applications
        completed = await session.execute(
            select(func.count(func.distinct(FunnelEvent.tg_user_id)))
            .where(FunnelEvent.event_type == "completed")
        )
        total_completed = completed.scalar() or 0

        # Declined
        declined = await session.execute(
            select(func.count(func.distinct(FunnelEvent.tg_user_id)))
            .where(FunnelEvent.event_type == "declined")
        )
        total_declined = declined.scalar() or 0

    if not rows and total_starts == 0:
        await message.answer("No funnel data yet.")
        return

    # Build step completion counts
    step_counts = {}
    decline_counts = {}
    for event_type, step_name, count in rows:
        if event_type == "step_completed":
            step_counts[step_name or "unknown"] = count
        elif event_type == "declined":
            decline_counts[step_name or "unknown"] = count

    step_order = ["name", "has_pc", "age", "study_work", "english",
                  "pc_confidence", "cpu", "gpu", "internet", "start_date", "contact"]

    lines = [
        f"📊 Funnel Analytics",
        f"",
        f"👤 /start: {total_starts}",
        f"📝 Apply Now: {total_applies}",
        f"",
        f"Step completions:",
    ]
    for step in step_order:
        c = step_counts.get(step, 0)
        lines.append(f"  {step:>14}: {c}")

    lines.append(f"\n✅ Completed: {total_completed}")
    lines.append(f"❌ Declined: {total_declined}")

    if decline_counts:
        lines.append(f"\nDecline reasons:")
        for step, count in sorted(decline_counts.items(), key=lambda x: -x[1]):
            lines.append(f"  {step}: {count}")

    await message.answer("\n".join(lines))


# ═══ UTM SOURCE ANALYTICS ═══

@router.message(Command("sources"), F.func(is_admin))
async def cmd_sources(message: Message):
    """Show candidate acquisition by UTM source."""
    async with async_session() as session:
        # From candidates table
        result = await session.execute(
            select(Candidate.utm_source, func.count(Candidate.id))
            .group_by(Candidate.utm_source)
            .order_by(func.count(Candidate.id).desc())
        )
        candidate_sources = result.all()

        # From funnel events (includes those who didn't finish)
        events = await session.execute(
            select(FunnelEvent.data, func.count(func.distinct(FunnelEvent.tg_user_id)))
            .where(FunnelEvent.event_type == "utm_source")
            .group_by(FunnelEvent.data)
        )
        event_sources = events.all()

    lines = ["📊 Traffic Sources\n"]

    if event_sources:
        lines.append("All visitors (from funnel events):")
        for data_json, count in event_sources:
            source = data_json or "unknown"
            lines.append(f"  {source}: {count}")

    lines.append("")
    if candidate_sources:
        lines.append("Completed applications:")
        for source, count in candidate_sources:
            lines.append(f"  {source or 'direct'}: {count}")
    else:
        lines.append("No completed applications yet.")

    await message.answer("\n".join(lines))


# ═══ /candidates — list recent candidates ═══

@router.message(Command("candidates"), F.func(is_admin))
async def cmd_candidates(message: Message):
    """List recent candidates with status."""
    async with async_session() as session:
        result = await session.execute(
            select(Candidate)
            .order_by(Candidate.created_at.desc())
            .limit(20)
        )
        candidates = result.scalars().all()

    if not candidates:
        await message.answer("No candidates yet.")
        return

    lines = ["Recent candidates:\n"]
    for c in candidates:
        icon = {"screened": "🟡", "interview_invited": "🟢", "active": "✅",
                "declined": "❌", "churned": "⚫", "new": "⚪"}.get(c.status, "❓")
        flags = []
        if c.age and c.age < 18:
            flags.append("U18")
        if not c.has_pc:
            flags.append("NoPC")
        if c.english_level == "Beginner":
            flags.append("LowEng")
        if c.hardware_compatible is False:
            flags.append("BadHW")
        flag_str = f" [{','.join(flags)}]" if flags else ""
        lines.append(
            f"{icon} {c.name} | @{c.tg_username or 'N/A'} | "
            f"{c.status} | {c.score or '-'}/100{flag_str}"
        )

    await message.answer("\n".join(lines))


# ═══ HELP ═══

@router.message(Command("slots"), F.func(is_admin))
async def cmd_slots(message: Message):
    """Check available interview slots from HuntMe CRM."""
    from bot.services import huntme_crm

    await message.answer("Checking CRM connection...")
    ok, info = await huntme_crm.check_connection()
    if not ok:
        await message.answer(f"CRM: {info}")
        return

    slots = await huntme_crm.get_available_slots(office_id=95)
    if not slots:
        await message.answer("No slots available.")
        return

    lines = [f"Available slots (Office 95 — ENG+OTHER):\n"]
    total = 0
    for date_str in sorted(slots.keys(), key=lambda d: d.split(".")[::-1]):
        times = slots[date_str]
        total += len(times)
        times_str = ", ".join(times)
        lines.append(f"  {date_str}: {times_str}")

    lines.append(f"\nTotal: {total} slots across {len(slots)} days")
    await message.answer("\n".join(lines))


@router.message(Command("help"), F.func(is_admin))
async def cmd_help(message: Message):
    await message.answer(
        "Admin commands:\n\n"
        "/pipeline — Candidate counts by status\n"
        "/candidates — Recent candidates list\n"
        "/funnel — Step-by-step conversion analytics\n"
        "/sources — Traffic source analytics (UTM)\n"
        "/stats — Earnings estimate\n"
        "/msg <id> <text> — Send message to candidate\n"
        "/post [ph|ng|latam] — Generate job posting\n"
        "/screen <text> — AI-screen text\n"
        "/slots — Check CRM interview slots\n"
        "/ref — Referral link\n"
        "/help — This message\n\n"
        "Inline buttons on each application:\n"
        "✅ Interview — send invite\n"
        "❌ Reject — send rejection\n"
        "💬 Message — send custom text\n\n"
        "Reply to any ❓ QUESTION message to answer the candidate."
    )
