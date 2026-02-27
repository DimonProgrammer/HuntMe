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
from sqlalchemy import delete, select

from bot.config import config
from bot.database import async_session
from bot.database.models import Candidate, SlotReservation
from bot.messages import msg
from bot.services import huntme_crm
from bot.services.huntme_crm import _MANILA_TZ

logger = logging.getLogger(__name__)
router = Router()


class InterviewBooking(StatesGroup):
    waiting_birth_date = State()
    waiting_phone = State()
    waiting_experience = State()
    waiting_slot_choice = State()
    waiting_slot_preferred = State()
    waiting_crm_approval = State()  # slot chosen, pending admin approval


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
    data = await state.get_data()
    lang = data.get("language", "en")
    m = msg(lang)
    await state.update_data(booking_tg_user_id=tg_user_id)
    await state.set_state(InterviewBooking.waiting_birth_date)
    await message.answer(m.BOOKING_START)


# ═══ BIRTH DATE ═══


@router.message(InterviewBooking.waiting_birth_date, F.text)
async def on_birth_date(message: Message, state: FSMContext):
    data = await state.get_data()
    lang = data.get("language", "en")
    m = msg(lang)
    raw = message.text.strip()

    birth_date = _parse_date(raw)
    if not birth_date:
        await message.answer(m.BOOKING_DATE_FAIL)
        return

    await state.update_data(birth_date=birth_date)
    await state.set_state(InterviewBooking.waiting_phone)
    await message.answer(m.BOOKING_PHONE)


# ═══ PHONE ═══


@router.message(InterviewBooking.waiting_phone, F.text)
async def on_phone(message: Message, state: FSMContext):
    data = await state.get_data()
    lang = data.get("language", "en")
    m = msg(lang)
    raw = message.text.strip()
    digits, country = huntme_crm.parse_phone(raw)

    if len(digits) < 7:
        await message.answer(m.BOOKING_PHONE_FAIL)
        return

    await state.update_data(phone_number=digits, phone_country=country)

    await state.set_state(InterviewBooking.waiting_experience)
    await message.answer(m.BOOKING_EXPERIENCE)


# ═══ EXPERIENCE ═══


@router.message(InterviewBooking.waiting_experience, F.text)
async def on_experience(message: Message, state: FSMContext):
    data = await state.get_data()
    lang = data.get("language", "en")
    m = msg(lang)
    experience = message.text.strip()
    await state.update_data(experience=experience)

    await message.answer(m.BOOKING_FETCHING_SLOTS)
    await _show_slots(message, state)


# ═══ SLOT SELECTION ═══


async def _try_reserve_slot(slot_str: str, tg_user_id: int) -> bool:
    """Claim a slot. Returns False if another user has it (non-expired within 30 min)."""
    async with async_session() as session:
        existing = await session.get(SlotReservation, slot_str)
        now = _dt.datetime.utcnow()
        if existing:
            age_min = (now - existing.reserved_at).total_seconds() / 60
            if age_min < 30 and existing.tg_user_id != tg_user_id:
                return False
            existing.tg_user_id = tg_user_id
            existing.reserved_at = now
        else:
            session.add(SlotReservation(slot_str=slot_str, tg_user_id=tg_user_id, reserved_at=now))
        await session.commit()
        return True


async def _release_slot(slot_str: str):
    """Release a slot reservation (on reject or re-book)."""
    if not slot_str:
        return
    try:
        async with async_session() as session:
            await session.execute(
                delete(SlotReservation).where(SlotReservation.slot_str == slot_str)
            )
            await session.commit()
    except Exception:
        logger.debug("Failed to release slot %s", slot_str)


def _filter_slots_by_preference(
    slots: dict, preferred: str
) -> tuple[list[str], bool]:
    """Filter/reorder available slots based on free-text preference (EN + RU).

    Returns (filtered_slots, preference_was_matched).
    Falls back to nearest slots if nothing matches.
    """
    text = preferred.lower()

    day_keywords: dict[int, list[str]] = {
        0: ["monday", "mon", "понедельник", "пн"],
        1: ["tuesday", "tue", "вторник", "вт"],
        2: ["wednesday", "wed", "среда", "среду", "ср"],
        3: ["thursday", "thu", "четверг", "чт"],
        4: ["friday", "fri", "пятница", "пятницу", "пт"],
        5: ["saturday", "sat", "суббота", "субботу", "сб"],
        6: ["sunday", "sun", "воскресенье", "вс"],
    }
    time_keywords: dict[tuple[int, int], list[str]] = {
        (6, 12):  ["morning", "утро", "утром", "утра"],
        (12, 17): ["afternoon", "noon", "день", "дня", "днём", "днем"],
        (17, 24): ["evening", "вечер", "вечером", "вечера"],
        (21, 24): ["night", "late", "ночь", "ночью"],
    }

    preferred_day: Optional[int] = None
    preferred_hours: Optional[tuple[int, int]] = None

    for day_num, keywords in day_keywords.items():
        if any(kw in text for kw in keywords):
            preferred_day = day_num
            break

    for (h_min, h_max), keywords in time_keywords.items():
        if any(kw in text for kw in keywords):
            preferred_hours = (h_min, h_max)
            break

    all_slots = huntme_crm.pick_nearest_slots(slots, count=20)

    if preferred_day is None and preferred_hours is None:
        return all_slots[:5], False  # nothing parsed

    matched = []
    partial = []

    for slot_str in all_slots:
        try:
            dt = _dt.datetime.strptime(slot_str, "%d.%m.%Y %H:%M")
            day_ok = preferred_day is None or dt.weekday() == preferred_day
            time_ok = preferred_hours is None or preferred_hours[0] <= dt.hour < preferred_hours[1]
            if day_ok and time_ok:
                matched.append(slot_str)
            elif day_ok or time_ok:
                partial.append(slot_str)
        except Exception:
            continue

    if matched:
        return matched[:5], True
    if partial:
        return partial[:5], False
    return all_slots[:5], False


async def _show_slots(
    message: Message, state: FSMContext, preferred_text: str = None
):
    """Fetch fresh slots from CRM and show as inline buttons."""
    data = await state.get_data()
    lang = data.get("language", "en")
    m = msg(lang)
    tg_user_id = data.get("booking_tg_user_id", 0)

    slots = await huntme_crm.get_available_slots(office_id=95)

    retry_kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔄 Try Again", callback_data="retry_slots")],
        [InlineKeyboardButton(text=m.BTN_BACK_MENU, callback_data="back_main")],
    ])

    if slots is None:
        await message.answer(m.BOOKING_SLOTS_ERROR, reply_markup=retry_kb)
        await state.set_state(InterviewBooking.waiting_slot_choice)
        return

    if not slots:
        await message.answer(m.BOOKING_NO_SLOTS, reply_markup=retry_kb)
        await state.set_state(InterviewBooking.waiting_slot_choice)
        return

    # Cleanup expired reservations
    try:
        async with async_session() as session:
            await session.execute(
                delete(SlotReservation).where(
                    SlotReservation.reserved_at < _dt.datetime.utcnow() - _dt.timedelta(minutes=30)
                )
            )
            await session.commit()
    except Exception:
        logger.debug("Failed to cleanup expired slot reservations")

    # Fetch active reservations (not mine)
    reserved: set = set()
    try:
        async with async_session() as session:
            result = await session.execute(
                select(SlotReservation.slot_str).where(SlotReservation.tg_user_id != tg_user_id)
            )
            reserved = {row[0] for row in result}
    except Exception:
        logger.debug("Failed to fetch slot reservations")

    # Also filter slots held by pending/invited candidates (SlotReservation expires in 30m,
    # but candidates.huntme_crm_slot persists until admin approve/reject)
    try:
        async with async_session() as session:
            cand_result = await session.execute(
                select(Candidate.huntme_crm_slot)
                .where(Candidate.huntme_crm_slot.isnot(None))
                .where(Candidate.status.in_(["pending_crm_approval", "interview_invited"]))
                .where(Candidate.tg_user_id != tg_user_id)
            )
            reserved.update(row[0] for row in cand_result if row[0])
    except Exception:
        logger.debug("Failed to fetch candidate slot reservations")

    # Filter slots based on preference or pick nearest
    if preferred_text:
        filtered, pref_matched = _filter_slots_by_preference(slots, preferred_text)
        nearest = [s for s in filtered if s not in reserved][:5]
        header = m.BOOKING_PREF_MATCH if pref_matched else m.BOOKING_PREF_NOMATCH
    else:
        all_nearest = huntme_crm.pick_nearest_slots(slots, count=7)
        nearest = [s for s in all_nearest if s not in reserved][:5]
        header = m.BOOKING_SLOTS_HEADER

    if not nearest:
        await message.answer(m.BOOKING_SLOTS_TOO_SOON, reply_markup=retry_kb)
        await state.set_state(InterviewBooking.waiting_slot_choice)
        return

    buttons = []
    for slot_str in nearest:
        display = _format_slot_display(slot_str)
        cb_data = f"book_{slot_str.replace('.', '-').replace(' ', '_')}"
        buttons.append([InlineKeyboardButton(text=display, callback_data=cb_data)])

    buttons.append([InlineKeyboardButton(text=m.BTN_OTHER_TIME, callback_data="book_other")])

    keyboard = InlineKeyboardMarkup(inline_keyboard=buttons)

    await state.set_state(InterviewBooking.waiting_slot_choice)
    await message.answer(header, reply_markup=keyboard)


@router.callback_query(InterviewBooking.waiting_slot_choice, F.data.startswith("book_"))
async def on_slot_chosen(callback: CallbackQuery, state: FSMContext):
    await callback.answer()
    data = await state.get_data()
    lang = data.get("language", "en")
    m = msg(lang)

    if callback.data == "book_other":
        await state.set_state(InterviewBooking.waiting_slot_preferred)
        # Remove slot buttons so they can't be clicked after choosing "Other time"
        try:
            await callback.message.edit_reply_markup(reply_markup=None)
        except Exception:
            pass
        await callback.message.answer(m.BOOKING_OTHER_TIME)
        return

    encoded = callback.data.removeprefix("book_")
    slot_str = encoded.replace("-", ".").replace("_", " ")

    await callback.message.edit_text(m.BOOKING_CHECKING)

    slots = await huntme_crm.get_available_slots(office_id=95)
    if not slots:
        await callback.message.edit_text(m.BOOKING_RETRY)
        await _show_slots(callback.message, state)
        return

    date_part, time_part = slot_str.split(" ", 1)
    if date_part not in slots or time_part not in slots[date_part]:
        await callback.message.edit_text(m.BOOKING_SLOT_TAKEN)
        await _show_slots(callback.message, state)
        return

    # Try to reserve the slot (race condition protection)
    tg_user_id = data.get("booking_tg_user_id", callback.from_user.id)
    claimed = await _try_reserve_slot(slot_str, tg_user_id)
    if not claimed:
        await callback.message.edit_text(m.BOOKING_SLOT_RESERVED)
        await _show_slots(callback.message, state)
        return

    await callback.message.edit_text(m.BOOKING_CONFIRMING)
    await _request_crm_approval(callback.message, state, slot_str)


@router.callback_query(InterviewBooking.waiting_slot_choice, F.data == "retry_slots")
async def on_retry_slots(callback: CallbackQuery, state: FSMContext):
    """Retry fetching slots after an error."""
    await callback.answer()
    try:
        await callback.message.edit_text("Looking for available interview times...")
    except Exception:
        pass
    await _show_slots(callback.message, state)


@router.message(InterviewBooking.waiting_slot_preferred, F.text)
async def on_slot_preferred(message: Message, state: FSMContext):
    """Candidate specified preferred times — re-fetch and filter."""
    data = await state.get_data()
    lang = data.get("language", "en")
    m = msg(lang)
    preferred = message.text.strip()
    await state.update_data(preferred_time=preferred)

    await message.answer(m.BOOKING_PREFERRED_ACK)
    await _show_slots(message, state, preferred_text=preferred)


# ═══ ADMIN APPROVAL → CRM SUBMISSION ═══


async def _request_crm_approval(message: Message, state: FSMContext, slot_str: str):
    """Save booking data to DB and send admin a preview for approval."""
    data = await state.get_data()
    lang = data.get("language", "en")
    m = msg(lang)
    # Fallback to chat ID if booking_tg_user_id somehow missing from FSM
    tg_user_id = data.get("booking_tg_user_id") or message.chat.id

    # Load candidate from DB; create from FSM data if _save_candidate failed earlier
    candidate = None
    try:
        async with async_session() as session:
            result = await session.execute(
                select(Candidate).where(Candidate.tg_user_id == tg_user_id)
            )
            candidate = result.scalar_one_or_none()
            if not candidate:
                logger.warning(
                    "Candidate %s not found in DB during booking — creating from FSM data",
                    tg_user_id,
                )
                candidate = Candidate(
                    tg_user_id=tg_user_id,
                    name=data.get("name", "Unknown"),
                    candidate_type=data.get("candidate_type", "operator"),
                    language=data.get("language", "en"),
                    status="screened",
                    score=data.get("ai_score"),
                    recommendation=data.get("ai_recommendation"),
                    hardware_compatible=data.get("hardware_compatible"),
                )
                session.add(candidate)
                await session.commit()
    except Exception:
        logger.exception("Failed to load/create candidate for CRM approval")

    if not candidate:
        await message.answer(m.BOOKING_DATA_ERROR)
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
    change_kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=m.BTN_CHANGE_SLOT, callback_data="change_slot")],
    ])
    await message.answer(m.BOOKING_SLOT_CHOSEN.format(display=display), reply_markup=change_kb)
    # Keep state (don't clear) so candidate can change slot before admin approval
    await state.set_state(InterviewBooking.waiting_crm_approval)

    # Same-day urgency check
    now_manila = _dt.datetime.now(_MANILA_TZ)
    urgency_block = ""
    try:
        slot_dt = _dt.datetime.strptime(slot_str, "%d.%m.%Y %H:%M").replace(tzinfo=_MANILA_TZ)
        is_same_day = slot_dt.date() == now_manila.date()
        hours_until = (slot_dt - now_manila).total_seconds() / 3600
        if is_same_day:
            urgency_block = (
                f"\n\n⚡ SAME-DAY BOOKING — {hours_until:.1f}h until slot!\n"
                f"📩 Contact @HuntMeHelp BEFORE approving so they confirm faster."
            )
    except Exception:
        pass

    # Send admin the full preview + approve/reject buttons
    # Use FSM state data as fallback for screening fields (in case DB wasn't updated)
    tg_handle = candidate.tg_username or str(tg_user_id)
    score_val = candidate.score or data.get("ai_score") or 0
    rec_val = candidate.recommendation or data.get("ai_recommendation") or "N/A"
    hw_compatible = candidate.hardware_compatible
    hw_icon = (
        "Compatible" if hw_compatible is True
        else "Incompatible" if hw_compatible is False
        else "Not checked"
    )
    preview = (
        f"📋 CRM SUBMISSION — APPROVAL NEEDED\n\n"
        f"Candidate: {candidate.name} (@{tg_handle})\n"
        f"ID: {tg_user_id}\n"
        f"Score: {score_val}/100 ({rec_val})\n\n"
        f"📝 Form data for CRM:\n"
        f"  Birth date: {data.get('birth_date', 'N/A')}\n"
        f"  Phone: {data.get('phone_number', 'N/A')} ({data.get('phone_country', 'N/A')})\n"
        f"  Slot: {display}\n\n"
        f"📊 Screening data:\n"
        f"  English: {candidate.english_level or data.get('english_level') or 'N/A'}\n"
        f"  Study/Work: {candidate.study_status or data.get('study_status') or 'N/A'}\n"
        f"  PC confidence: {candidate.pc_confidence or data.get('pc_confidence') or 'N/A'}\n"
        f"  Hardware: {hw_icon}\n"
        f"  CPU: {candidate.cpu_model or data.get('cpu_model') or 'N/A'}\n"
        f"  GPU: {candidate.gpu_model or data.get('gpu_model') or 'N/A'}\n"
        f"  Internet: {candidate.internet_speed or data.get('internet_speed') or 'N/A'}\n"
        f"  Start: {candidate.start_date or data.get('start_date') or 'N/A'}\n"
        f"  Experience: {data.get('experience', 'N/A')}"
        f"{urgency_block}"
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
    tg_user_id = int(callback.data.removeprefix("crm_ok_"))

    # Immediately disable buttons to prevent double-click
    try:
        await callback.message.edit_text(
            callback.message.text + "\n\n⏳ Processing..."
        )
    except Exception:
        pass
    await callback.answer("Processing CRM submission...")

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
            callback.message.text.replace("\n\n⏳ Processing...", "")
            + "\n\n❌ ERROR: candidate or slot data not found"
        )
        return

    # Guard: prevent double submission
    if candidate.huntme_crm_submitted:
        await callback.message.edit_text(
            callback.message.text.replace("\n\n⏳ Processing...", "")
            + "\n\n⚠️ Already submitted to CRM"
        )
        return

    # Guard: prevent submitting for declined candidates
    if candidate.status == "declined":
        await callback.message.edit_text(
            callback.message.text.replace("\n\n⏳ Processing...", "")
            + "\n\n❌ Candidate was already declined"
        )
        return

    slot_str = candidate.huntme_crm_slot
    tg_handle = candidate.tg_username or str(tg_user_id)

    # Safe slot parsing
    if " " not in slot_str:
        await callback.message.edit_text(
            callback.message.text.replace("\n\n⏳ Processing...", "")
            + "\n\n❌ ERROR: invalid slot format"
        )
        return

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

        # Release slot reservation (no longer needed after successful submit)
        await _release_slot(slot_str)

        # Notify candidate with full invite message
        cand_lang = cand.language if cand else "en"
        cm = msg(cand_lang)
        cal_link = _google_calendar_link(slot_str, display)
        invite_text = cm.BOOKING_INVITE.format(display=display)
        if cal_link:
            invite_text += f"\n\n📆 [Add to Google Calendar]({cal_link})"
        try:
            await callback.bot.send_message(
                tg_user_id,
                invite_text,
                parse_mode="Markdown",
            )
        except Exception:
            logger.debug("Failed to notify candidate about confirmed booking")

        await callback.message.edit_text(
            callback.message.text.replace("\n\n⏳ Processing...", "")
            + f"\n\n✅ SUBMITTED TO CRM — {display}"
        )
    else:
        logger.warning("CRM submit failed for %s: %s", tg_user_id, error)
        await callback.message.edit_text(
            callback.message.text.replace("\n\n⏳ Processing...", "")
            + f"\n\n⚠️ CRM SUBMIT FAILED: {error}"
        )


@router.callback_query(F.data.startswith("crm_no_"))
async def on_crm_reject(callback: CallbackQuery):
    """Admin rejected CRM submission."""
    await callback.answer("Rejected")
    tg_user_id = int(callback.data.removeprefix("crm_no_"))

    # Revert status and release slot
    slot_to_release = None
    try:
        async with async_session() as session:
            result = await session.execute(
                select(Candidate).where(Candidate.tg_user_id == tg_user_id)
            )
            cand = result.scalar_one_or_none()
            if cand:
                slot_to_release = cand.huntme_crm_slot
                cand.status = "screened"
                cand.huntme_crm_slot = None
                await session.commit()
    except Exception:
        logger.exception("Failed to update candidate after CRM rejection")

    await _release_slot(slot_to_release)

    # Notify candidate — get language from candidate record
    cand_lang = cand.language if cand else "en"
    cm = msg(cand_lang)
    try:
        await callback.bot.send_message(tg_user_id, cm.BOOKING_SOFT_REJECT)
    except Exception:
        logger.debug("Failed to notify candidate about CRM rejection")

    await callback.message.edit_text(
        callback.message.text + "\n\n❌ REJECTED — not submitted to CRM"
    )


# ═══ CHANGE SLOT (candidate re-picks before admin approval) ═══


@router.callback_query(InterviewBooking.waiting_crm_approval, F.data == "change_slot")
async def on_change_slot(callback: CallbackQuery, state: FSMContext):
    """Candidate clicked 'Change slot' before admin approved — re-show slot picker."""
    await callback.answer()
    data = await state.get_data()
    lang = data.get("language", "en")
    m = msg(lang)
    tg_user_id = callback.from_user.id

    slot_to_release = None
    try:
        async with async_session() as session:
            result = await session.execute(
                select(Candidate).where(Candidate.tg_user_id == tg_user_id)
            )
            cand = result.scalar_one_or_none()
            if cand and cand.status == "pending_crm_approval":
                slot_to_release = cand.huntme_crm_slot
                cand.huntme_crm_slot = None
                cand.status = "screened"
                await session.commit()
            elif cand:
                # Admin already acted — don't allow re-pick
                await callback.answer(
                    "Your booking is already confirmed!" if lang == "en"
                    else "Бронирование уже подтверждено!",
                    show_alert=True,
                )
                return
    except Exception:
        logger.exception("Failed to release slot on change request")
        return

    await _release_slot(slot_to_release)

    # Remove the Change slot button from the confirmation message
    try:
        await callback.message.edit_reply_markup(reply_markup=None)
    except Exception:
        pass

    await callback.message.answer(m.BOOKING_CHANGE_SLOT_PROMPT)
    await _show_slots(callback.message, state)


# ═══ REBOOK (slot disappeared after admin delay) ═══


async def _rebook_candidate(bot, tg_user_id: int, fresh_slots: dict):
    """Slot disappeared — notify candidate and show fresh slots to pick from."""
    # Get candidate language from DB
    cand_lang = "en"
    try:
        async with async_session() as session:
            result = await session.execute(
                select(Candidate).where(Candidate.tg_user_id == tg_user_id)
            )
            cand = result.scalar_one_or_none()
            if cand:
                cand_lang = cand.language or "en"
    except Exception:
        pass
    m = msg(cand_lang)

    nearest = huntme_crm.pick_nearest_slots(fresh_slots, count=5) if fresh_slots else []

    if not nearest:
        await bot.send_message(tg_user_id, m.REBOOK_NO_SLOTS)
        return

    buttons = []
    for slot_str in nearest:
        display = _format_slot_display(slot_str)
        cb_data = f"rebook_{tg_user_id}_{slot_str.replace('.', '-').replace(' ', '_')}"
        buttons.append([InlineKeyboardButton(text=display, callback_data=cb_data)])

    keyboard = InlineKeyboardMarkup(inline_keyboard=buttons)

    await bot.send_message(tg_user_id, m.REBOOK_PICK_NEW, reply_markup=keyboard)


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
        await callback.message.edit_text(msg("en").REBOOK_CHECK_FAIL)
        return

    # Get candidate language
    cand_lang = "en"
    try:
        async with async_session() as session:
            result = await session.execute(
                select(Candidate).where(Candidate.tg_user_id == tg_user_id)
            )
            c = result.scalar_one_or_none()
            if c:
                cand_lang = c.language or "en"
    except Exception:
        pass
    m = msg(cand_lang)

    if slots:
        date_part, time_part = slot_str.split(" ", 1)
        if date_part not in slots or time_part not in slots[date_part]:
            await callback.message.edit_text(m.REBOOK_SLOT_TAKEN_AGAIN)
            await _rebook_candidate(callback.bot, tg_user_id, slots)
            return

    # Try to reserve the new slot
    claimed = await _try_reserve_slot(slot_str, tg_user_id)
    if not claimed:
        # Get language for message
        cand_lang_rb = "en"
        try:
            async with async_session() as session:
                rb_result = await session.execute(
                    select(Candidate).where(Candidate.tg_user_id == tg_user_id)
                )
                rb_cand = rb_result.scalar_one_or_none()
                if rb_cand:
                    cand_lang_rb = rb_cand.language or "en"
        except Exception:
            pass
        await callback.message.edit_text(msg(cand_lang_rb).BOOKING_SLOT_RESERVED)
        await _rebook_candidate(callback.bot, tg_user_id, slots)
        return

    # Update candidate's slot in DB (release old, set new)
    old_slot = None
    try:
        async with async_session() as session:
            result = await session.execute(
                select(Candidate).where(Candidate.tg_user_id == tg_user_id)
            )
            cand = result.scalar_one_or_none()
            if cand:
                old_slot = cand.huntme_crm_slot
                cand.huntme_crm_slot = slot_str
                cand.status = "pending_crm_approval"
                await session.commit()
    except Exception:
        logger.exception("Failed to update rebook slot")

    if old_slot and old_slot != slot_str:
        await _release_slot(old_slot)

    display = _format_slot_display(slot_str)
    await callback.message.edit_text(m.REBOOK_CONFIRMED.format(display=display))

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


def _google_calendar_link(slot_str: str, display: str) -> Optional[str]:
    """Generate Google Calendar 'Add to Calendar' link for the interview slot.

    slot_str: '28.02.2026 19:00' (Manila time, UTC+8)
    Returns URL string or None on error.
    """
    try:
        import urllib.parse
        slot_dt = _dt.datetime.strptime(slot_str, "%d.%m.%Y %H:%M")
        # Manila is UTC+8 → subtract 8h to get UTC
        slot_utc = slot_dt - _dt.timedelta(hours=8)
        end_utc = slot_utc + _dt.timedelta(hours=1)
        fmt = "%Y%m%dT%H%M%SZ"
        title = urllib.parse.quote("Interview — Apex Talent (Live Stream Operator)")
        details = urllib.parse.quote(
            "Join via Zoom or Discord.\n"
            "Manager contact: @hr_helper31 (Telegram) or wa.me/14433037260 (WhatsApp)"
        )
        dates = f"{slot_utc.strftime(fmt)}/{end_utc.strftime(fmt)}"
        return (
            f"https://calendar.google.com/calendar/render"
            f"?action=TEMPLATE&text={title}&dates={dates}&details={details}"
        )
    except Exception:
        return None


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


# ═══ INTERVIEW DAY CALLBACKS ═══


@router.callback_query(F.data == "interview_confirm")
async def on_interview_confirm(callback: CallbackQuery):
    """Candidate confirmed they'll attend the interview."""
    await callback.answer()
    tg_user_id = callback.from_user.id
    cand_lang = "en"
    try:
        async with async_session() as session:
            result = await session.execute(
                select(Candidate).where(Candidate.tg_user_id == tg_user_id)
            )
            cand = result.scalar_one_or_none()
            if cand:
                cand_lang = cand.language or "en"
    except Exception:
        pass
    m = msg(cand_lang)
    try:
        await callback.message.edit_text(m.INTERVIEW_CONFIRMED_REPLY)
    except Exception:
        pass


@router.callback_query(F.data == "interview_cancel")
async def on_interview_cancel(callback: CallbackQuery):
    """Candidate said they can't make it."""
    await callback.answer()
    tg_user_id = callback.from_user.id
    cand_lang = "en"
    try:
        async with async_session() as session:
            result = await session.execute(
                select(Candidate).where(Candidate.tg_user_id == tg_user_id)
            )
            cand = result.scalar_one_or_none()
            if cand:
                cand_lang = cand.language or "en"
    except Exception:
        pass
    m = msg(cand_lang)
    try:
        await callback.message.edit_text(m.INTERVIEW_CANCEL_REPLY)
    except Exception:
        pass


def _format_slot_display(slot_str: str) -> str:
    """Convert '02.03.2026 16:00' to 'Mon, Mar 2 at 16:00'."""
    try:
        dt = _dt.datetime.strptime(slot_str, "%d.%m.%Y %H:%M")
        return dt.strftime("%a, %b %d at %H:%M")
    except ValueError:
        return slot_str
