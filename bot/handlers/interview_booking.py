"""Interview booking flow — extra questions + slot selection + admin approval + CRM submit.

Standalone router. NOT connected to main.py until tested.
Called after AI screening gives PASS recommendation.

Flow: birth_date → phone → experience → show slots → confirm →
      admin approval → submit to CRM → notify candidate
"""

import datetime as _dt
import json
import logging
import re
from typing import Optional

from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup, Message
from sqlalchemy import select

from bot.config import config
from bot.database import async_session
from bot.database.models import Candidate
from bot.services import huntme_crm

logger = logging.getLogger(__name__)
router = Router()


class InterviewBooking(StatesGroup):
    waiting_birth_date = State()
    waiting_phone = State()
    waiting_experience = State()
    waiting_slot_choice = State()
    waiting_slot_preferred = State()


# ═══ ENTRY POINT ═══


@router.callback_query(F.data == "start_booking")
async def on_start_booking_click(callback: CallbackQuery, state: FSMContext):
    """Candidate clicked 'Book Interview' button (MAYBE candidates approved by admin)."""
    await callback.answer()
    await start_booking(callback.message, state, callback.from_user.id)


async def start_booking(message: Message, state: FSMContext, tg_user_id: int):
    """Start interview booking flow for a PASS candidate.

    Called from operator_flow after screening. Sets FSM state and asks first question.
    """
    await state.update_data(booking_tg_user_id=tg_user_id)
    await state.set_state(InterviewBooking.waiting_birth_date)
    await message.answer(
        "Great news! You've been selected for an interview! 🎉\n\n"
        "We just need a couple more details to book your slot.\n\n"
        "What is your date of birth?\n"
        "Please enter in format: DD.MM.YYYY (e.g. 15.05.1998)"
    )


# ═══ BIRTH DATE ═══


@router.message(InterviewBooking.waiting_birth_date, F.text)
async def on_birth_date(message: Message, state: FSMContext):
    raw = message.text.strip()

    # Parse various date formats
    birth_date = _parse_date(raw)
    if not birth_date:
        await message.answer(
            "I couldn't understand that date format.\n"
            "Please enter your date of birth as DD.MM.YYYY (e.g. 15.05.1998)"
        )
        return

    await state.update_data(birth_date=birth_date)
    await state.set_state(InterviewBooking.waiting_phone)
    await message.answer(
        "What is your phone number (with country code)?\n"
        "For example: +639171234567 or +2348012345678"
    )


# ═══ PHONE ═══


@router.message(InterviewBooking.waiting_phone, F.text)
async def on_phone(message: Message, state: FSMContext):
    raw = message.text.strip()
    digits, country = huntme_crm.parse_phone(raw)

    if len(digits) < 7:
        await message.answer(
            "That doesn't look like a valid phone number.\n"
            "Please enter your full phone number with country code (e.g. +639171234567)"
        )
        return

    await state.update_data(phone_number=digits, phone_country=country)

    # Ask about experience before showing slots
    await state.set_state(InterviewBooking.waiting_experience)
    await message.answer(
        "One last question! Do you have any experience with:\n"
        "- Live streaming / content moderation\n"
        "- Customer service / virtual assistant\n"
        "- Any other online/remote work\n\n"
        "If yes, please briefly describe. If no, just say 'no experience'."
    )


# ═══ EXPERIENCE ═══


@router.message(InterviewBooking.waiting_experience, F.text)
async def on_experience(message: Message, state: FSMContext):
    experience = message.text.strip()
    await state.update_data(experience=experience)

    # Now fetch slots and show them
    await message.answer("Looking for available interview times...")
    await _show_slots(message, state)


# ═══ SLOT SELECTION ═══


async def _show_slots(
    message: Message, state: FSMContext, preferred_text: str = None
):
    """Fetch fresh slots from CRM and show as inline buttons."""
    slots = await huntme_crm.get_available_slots(office_id=95)

    if not slots:
        await message.answer(
            "No interview slots are available right now.\n"
            "We'll notify you as soon as new times open up. Hang tight! 🙏"
        )
        await state.set_state(InterviewBooking.waiting_slot_choice)
        return

    nearest = huntme_crm.pick_nearest_slots(slots, count=5)

    if not nearest:
        await message.answer(
            "All available slots are too soon to book.\n"
            "New slots should appear tomorrow. We'll be in touch! 🙏"
        )
        await state.set_state(InterviewBooking.waiting_slot_choice)
        return

    # Build inline keyboard with slot buttons
    buttons = []
    for slot_str in nearest:
        # Display friendly format: "Fri, Feb 28 at 18:00"
        display = _format_slot_display(slot_str)
        # Callback data: slot_<encoded>
        cb_data = f"book_{slot_str.replace('.', '-').replace(' ', '_')}"
        buttons.append([InlineKeyboardButton(text=display, callback_data=cb_data)])

    buttons.append([InlineKeyboardButton(text="Other time ⏰", callback_data="book_other")])

    keyboard = InlineKeyboardMarkup(inline_keyboard=buttons)

    text = "Here are the nearest available interview times (Manila time, GMT+8):\n\n"
    text += "Pick one that works best for you:"

    await state.set_state(InterviewBooking.waiting_slot_choice)
    await message.answer(text, reply_markup=keyboard)


@router.callback_query(InterviewBooking.waiting_slot_choice, F.data.startswith("book_"))
async def on_slot_chosen(callback: CallbackQuery, state: FSMContext):
    await callback.answer()

    if callback.data == "book_other":
        await state.set_state(InterviewBooking.waiting_slot_preferred)
        await callback.message.answer(
            "No problem! What days and times would work better for you?\n"
            "For example: 'weekday evenings' or 'March 3-5, any time'"
        )
        return

    # Decode slot from callback data: book_02-03-2026_16:00 → 02.03.2026 16:00
    encoded = callback.data.removeprefix("book_")
    slot_str = encoded.replace("-", ".").replace("_", " ")

    # Fresh check: verify slot is still available
    await callback.message.edit_text("Checking availability...")

    slots = await huntme_crm.get_available_slots(office_id=95)
    if not slots:
        await callback.message.edit_text(
            "Couldn't verify slot availability. Let me try again..."
        )
        await _show_slots(callback.message, state)
        return

    # Check if the selected slot is still in the available list
    date_part, time_part = slot_str.split(" ", 1)
    if date_part not in slots or time_part not in slots[date_part]:
        await callback.message.edit_text(
            "That slot was just taken! Here are updated options:"
        )
        await _show_slots(callback.message, state)
        return

    # Slot is available — request admin approval before submitting
    await callback.message.edit_text("Confirming your slot...")
    await _request_crm_approval(callback.message, state, slot_str)


@router.message(InterviewBooking.waiting_slot_preferred, F.text)
async def on_slot_preferred(message: Message, state: FSMContext):
    """Candidate specified preferred times — re-fetch and filter."""
    preferred = message.text.strip()
    await state.update_data(preferred_time=preferred)

    await message.answer(f"Got it! Let me check what's available around that time...")
    # For now, just re-show all slots (AI-based time matching can be added later)
    await _show_slots(message, state, preferred_text=preferred)


# ═══ ADMIN APPROVAL → CRM SUBMISSION ═══


async def _request_crm_approval(message: Message, state: FSMContext, slot_str: str):
    """Save booking data to DB and send admin a preview for approval."""
    data = await state.get_data()
    tg_user_id = data.get("booking_tg_user_id")

    # Load candidate from DB
    candidate = None
    try:
        async with async_session() as session:
            result = await session.execute(
                select(Candidate).where(Candidate.tg_user_id == tg_user_id)
            )
            candidate = result.scalar_one_or_none()
    except Exception:
        logger.exception("Failed to load candidate for CRM approval")

    if not candidate:
        await message.answer(
            "Something went wrong loading your data. "
            "Our team will contact you to schedule the interview manually. 🙏"
        )
        await state.clear()
        return

    # Save booking data to candidate record
    try:
        async with async_session() as session:
            result = await session.execute(
                select(Candidate).where(Candidate.tg_user_id == tg_user_id)
            )
            cand = result.scalar_one_or_none()
            if cand:
                cand.birth_date = data.get("birth_date")
                cand.phone_number = data.get("phone_number")
                cand.phone_country = data.get("phone_country")
                cand.experience = data.get("experience")
                cand.huntme_crm_slot = slot_str
                cand.status = "pending_crm_approval"
                await session.commit()
    except Exception:
        logger.exception("Failed to save booking data")

    # Tell candidate — admin will review manually
    display = _format_slot_display(slot_str)
    await message.answer(
        f"You've chosen: {display} (Manila time) ✅\n\n"
        f"Our admin will review and confirm your booking shortly.\n"
        f"You'll receive a confirmation message once it's approved. 🙏"
    )
    await state.clear()

    # Send admin the full preview + approve/reject buttons
    tg_handle = candidate.tg_username or str(tg_user_id)
    hw_icon = (
        "Compatible" if candidate.hardware_compatible
        else "Incompatible" if candidate.hardware_compatible is False
        else "Not checked"
    )
    preview = (
        f"📋 CRM SUBMISSION — APPROVAL NEEDED\n\n"
        f"Candidate: {candidate.name} (@{tg_handle})\n"
        f"ID: {tg_user_id}\n"
        f"Score: {candidate.score or 0}/100 ({candidate.recommendation or 'N/A'})\n\n"
        f"📝 Form data for CRM:\n"
        f"  Birth date: {data.get('birth_date', 'N/A')}\n"
        f"  Phone: {data.get('phone_number', 'N/A')} ({data.get('phone_country', 'N/A')})\n"
        f"  Slot: {display}\n\n"
        f"📊 Screening data:\n"
        f"  English: {candidate.english_level or 'N/A'}\n"
        f"  Study/Work: {candidate.study_status or 'N/A'}\n"
        f"  PC confidence: {candidate.pc_confidence or 'N/A'}\n"
        f"  Hardware: {hw_icon}\n"
        f"  CPU: {candidate.cpu_model or 'N/A'}\n"
        f"  GPU: {candidate.gpu_model or 'N/A'}\n"
        f"  Internet: {candidate.internet_speed or 'N/A'}\n"
        f"  Start: {candidate.start_date or 'N/A'}\n"
        f"  Experience: {data.get('experience', 'N/A')}"
    )
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(
                text="✅ Approve & Submit",
                callback_data=f"crm_ok_{tg_user_id}",
            ),
            InlineKeyboardButton(
                text="❌ Reject",
                callback_data=f"crm_no_{tg_user_id}",
            ),
        ],
    ])

    if config.ADMIN_CHAT_ID:
        try:
            await message.bot.send_message(
                config.ADMIN_CHAT_ID, preview, reply_markup=keyboard,
            )
        except Exception:
            logger.exception("Failed to send CRM approval request to admin")


@router.callback_query(F.data.startswith("crm_ok_"))
async def on_crm_approve(callback: CallbackQuery):
    """Admin approved — verify slot still exists, then submit to HuntMe CRM."""
    await callback.answer("Checking slot availability...")
    tg_user_id = int(callback.data.removeprefix("crm_ok_"))

    # Load candidate
    candidate = None
    try:
        async with async_session() as session:
            result = await session.execute(
                select(Candidate).where(Candidate.tg_user_id == tg_user_id)
            )
            candidate = result.scalar_one_or_none()
    except Exception:
        logger.exception("Failed to load candidate for CRM approve")

    if not candidate or not candidate.huntme_crm_slot:
        await callback.message.edit_text(
            callback.message.text + "\n\n❌ ERROR: candidate or slot data not found"
        )
        return

    slot_str = candidate.huntme_crm_slot
    tg_handle = candidate.tg_username or str(tg_user_id)

    # ── Verify slot is still available before submitting ──
    try:
        fresh_slots = await huntme_crm.get_available_slots(office_id=95)
    except Exception:
        logger.exception("Failed to fetch fresh slots for verification")
        fresh_slots = None

    if fresh_slots is not None:
        date_part, time_part = slot_str.split(" ", 1)
        if date_part not in fresh_slots or time_part not in fresh_slots[date_part]:
            # Slot disappeared — notify admin and re-show slots to candidate
            await callback.message.edit_text(
                callback.message.text
                + f"\n\n⚠️ SLOT GONE — {_format_slot_display(slot_str)} is no longer available. "
                f"Re-showing fresh slots to candidate."
            )
            await _rebook_candidate(callback.bot, tg_user_id, fresh_slots)
            return

    # Generate AI-powered CRM form answers
    crm_answers = await huntme_crm.generate_crm_answers(
        name=candidate.name,
        english_level=candidate.english_level or "Not specified",
        study_status=candidate.study_status or "Not specified",
        experience=candidate.experience or "No answer",
        pc_confidence=candidate.pc_confidence or "Not specified",
        hardware_compatible=(
            str(candidate.hardware_compatible)
            if candidate.hardware_compatible is not None else "Not checked"
        ),
        cpu_model=candidate.cpu_model or "Not specified",
        gpu_model=candidate.gpu_model or "Not specified",
        internet_speed=candidate.internet_speed or "Not specified",
        start_date=candidate.start_date or "Not specified",
        score=candidate.score or 0,
        recommendation=candidate.recommendation or "MAYBE",
        reasoning=candidate.notes or "No screening data",
    )

    # Submit to CRM
    success, error = await huntme_crm.submit_application(
        name=candidate.name,
        birth_date=candidate.birth_date or "01.01.2000",
        phone=candidate.phone_number or "",
        phone_country=candidate.phone_country or "ph",
        telegram=tg_handle,
        slot=slot_str,
        crm_answers=crm_answers,
        office_id=95,
    )

    display = _format_slot_display(slot_str)

    if success:
        # Update DB
        try:
            async with async_session() as session:
                result = await session.execute(
                    select(Candidate).where(Candidate.tg_user_id == tg_user_id)
                )
                cand = result.scalar_one_or_none()
                if cand:
                    cand.status = "interview_invited"
                    cand.huntme_crm_submitted = True
                    await session.commit()
        except Exception:
            logger.exception("Failed to update CRM status")

        # Notify candidate
        try:
            await callback.bot.send_message(
                tg_user_id,
                f"Your interview is confirmed! ✅\n\n"
                f"📅 {display}\n"
                f"🕐 Manila time (GMT+8)\n\n"
                f"The interview is a 30-40 minute video call where we'll:\n"
                f"• Explain the role in detail\n"
                f"• Answer all your questions\n"
                f"• Do a quick age verification\n\n"
                f"No additional registration needed — your slot is booked.\n"
                f"Looking forward to meeting you! 🙂"
            )
        except Exception:
            logger.debug("Failed to notify candidate about confirmed booking")

        await callback.message.edit_text(
            callback.message.text + f"\n\n✅ SUBMITTED TO CRM — {display}"
        )
    else:
        logger.warning("CRM submit failed for %s: %s", tg_user_id, error)
        await callback.message.edit_text(
            callback.message.text + f"\n\n⚠️ CRM SUBMIT FAILED: {error}"
        )


@router.callback_query(F.data.startswith("crm_no_"))
async def on_crm_reject(callback: CallbackQuery):
    """Admin rejected CRM submission."""
    await callback.answer("Rejected")
    tg_user_id = int(callback.data.removeprefix("crm_no_"))

    # Revert status
    try:
        async with async_session() as session:
            result = await session.execute(
                select(Candidate).where(Candidate.tg_user_id == tg_user_id)
            )
            cand = result.scalar_one_or_none()
            if cand:
                cand.status = "screened"
                cand.huntme_crm_slot = None
                await session.commit()
    except Exception:
        logger.exception("Failed to update candidate after CRM rejection")

    # Notify candidate
    try:
        await callback.bot.send_message(
            tg_user_id,
            "Thank you for your patience! Our team will contact you "
            "within 24 hours to confirm your interview time. 🙏"
        )
    except Exception:
        logger.debug("Failed to notify candidate about CRM rejection")

    await callback.message.edit_text(
        callback.message.text + "\n\n❌ REJECTED — not submitted to CRM"
    )


# ═══ REBOOK (slot disappeared after admin delay) ═══


async def _rebook_candidate(bot, tg_user_id: int, fresh_slots: dict):
    """Slot disappeared — notify candidate and show fresh slots to pick from."""
    nearest = huntme_crm.pick_nearest_slots(fresh_slots, count=5) if fresh_slots else []

    if not nearest:
        await bot.send_message(
            tg_user_id,
            "Sorry, the interview slot you selected is no longer available, "
            "and there are no other open times right now.\n"
            "We'll notify you as soon as new slots open up. 🙏"
        )
        return

    buttons = []
    for slot_str in nearest:
        display = _format_slot_display(slot_str)
        cb_data = f"rebook_{tg_user_id}_{slot_str.replace('.', '-').replace(' ', '_')}"
        buttons.append([InlineKeyboardButton(text=display, callback_data=cb_data)])

    keyboard = InlineKeyboardMarkup(inline_keyboard=buttons)

    await bot.send_message(
        tg_user_id,
        "Sorry, the slot you picked was just taken! 😔\n\n"
        "Here are the currently available times — please pick a new one:",
        reply_markup=keyboard,
    )


@router.callback_query(F.data.startswith("rebook_"))
async def on_rebook_slot(callback: CallbackQuery):
    """Candidate picks a new slot after their original one disappeared."""
    await callback.answer()
    # rebook_{user_id}_{encoded_slot}
    parts = callback.data.removeprefix("rebook_").split("_", 1)
    if len(parts) < 2:
        return
    tg_user_id = int(parts[0])
    encoded = parts[1]
    slot_str = encoded.replace("-", ".").replace("_", " ")

    # Verify this slot is still available
    try:
        slots = await huntme_crm.get_available_slots(office_id=95)
    except Exception:
        await callback.message.edit_text("Failed to check availability. Please try again later.")
        return

    if slots:
        date_part, time_part = slot_str.split(" ", 1)
        if date_part not in slots or time_part not in slots[date_part]:
            await callback.message.edit_text(
                "That slot was just taken too! Let me refresh..."
            )
            await _rebook_candidate(callback.bot, tg_user_id, slots)
            return

    # Update candidate's slot in DB
    try:
        async with async_session() as session:
            result = await session.execute(
                select(Candidate).where(Candidate.tg_user_id == tg_user_id)
            )
            cand = result.scalar_one_or_none()
            if cand:
                cand.huntme_crm_slot = slot_str
                cand.status = "pending_crm_approval"
                await session.commit()
    except Exception:
        logger.exception("Failed to update rebook slot")

    display = _format_slot_display(slot_str)
    await callback.message.edit_text(
        f"New slot selected: {display} (Manila time) ✅\n"
        f"Our admin will review and confirm your booking shortly. 🙏"
    )

    # Send new approval request to admin
    candidate = None
    try:
        async with async_session() as session:
            result = await session.execute(
                select(Candidate).where(Candidate.tg_user_id == tg_user_id)
            )
            candidate = result.scalar_one_or_none()
    except Exception:
        logger.exception("Failed to load candidate for rebook approval")
        return

    if not candidate:
        return

    tg_handle = candidate.tg_username or str(tg_user_id)
    hw_icon = (
        "Compatible" if candidate.hardware_compatible
        else "Incompatible" if candidate.hardware_compatible is False
        else "Not checked"
    )
    preview = (
        f"📋 CRM SUBMISSION — APPROVAL NEEDED (re-booked)\n\n"
        f"Candidate: {candidate.name} (@{tg_handle})\n"
        f"ID: {tg_user_id}\n"
        f"Score: {candidate.score or 0}/100 ({candidate.recommendation or 'N/A'})\n\n"
        f"📝 New slot: {display}\n"
        f"  Phone: {candidate.phone_number or 'N/A'} ({candidate.phone_country or 'N/A'})\n\n"
        f"📊 Screening data:\n"
        f"  English: {candidate.english_level or 'N/A'}\n"
        f"  Hardware: {hw_icon}\n"
        f"  CPU: {candidate.cpu_model or 'N/A'}\n"
        f"  GPU: {candidate.gpu_model or 'N/A'}"
    )
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(
                text="✅ Approve & Submit",
                callback_data=f"crm_ok_{tg_user_id}",
            ),
            InlineKeyboardButton(
                text="❌ Reject",
                callback_data=f"crm_no_{tg_user_id}",
            ),
        ],
    ])

    if config.ADMIN_CHAT_ID:
        try:
            await callback.bot.send_message(
                config.ADMIN_CHAT_ID, preview, reply_markup=keyboard,
            )
        except Exception:
            logger.exception("Failed to send rebook approval to admin")


# ═══ HELPERS ═══


def _parse_date(raw: str) -> Optional[str]:
    """Parse birth date from various formats. Returns dd.MM.yyyy or None."""
    raw = raw.strip()
    # Try common formats
    for fmt in ("%d.%m.%Y", "%d/%m/%Y", "%d-%m-%Y", "%Y-%m-%d", "%m/%d/%Y"):
        try:
            dt = _dt.datetime.strptime(raw, fmt)
            # Sanity check: not in the future, not too old
            if dt.year < 1950 or dt.year > 2010:
                continue
            return dt.strftime("%d.%m.%Y")
        except ValueError:
            continue
    return None


def _format_slot_display(slot_str: str) -> str:
    """Convert '02.03.2026 16:00' to 'Mon, Mar 2 at 16:00'."""
    try:
        dt = _dt.datetime.strptime(slot_str, "%d.%m.%Y %H:%M")
        return dt.strftime("%a, %b %d at %H:%M")
    except ValueError:
        return slot_str
