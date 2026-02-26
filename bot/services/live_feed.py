"""Live feed — mirrors candidate conversations to a Telegram group + inactivity alerts.

Usage:
    from bot.services import live_feed

    live_feed.init(bot, channel_id=..., admin_id=...)
    asyncio.create_task(live_feed.run_inactivity_checker())
"""

import asyncio
import logging
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)

# Human-readable step labels (FSM state suffix → label)
_STEP_LABELS: dict[str, str] = {
    "waiting_name":            "Имя",
    "waiting_has_pc":          "Наличие ПК",
    "waiting_no_pc_followup":  "Нет ПК — план",
    "waiting_age":             "Возраст",
    "waiting_study_work":      "Учёба / работа",
    "waiting_english":         "Английский",
    "waiting_pc_confidence":   "Уверенность в ПК",
    "waiting_cpu":             "CPU",
    "waiting_cpu_simple_age":  "CPU — возраст ПК",
    "waiting_cpu_simple_usage":"CPU — для чего",
    "waiting_gpu":             "GPU",
    "waiting_gpu_simple_gaming":"GPU — игры",
    "waiting_internet":        "Интернет",
    "waiting_start_date":      "Дата начала",
    "waiting_contact":         "Контакт",
}

# ── In-memory state (single-process, resets on redeploy — that's fine) ─────────
_last_cand_msg:  dict[int, datetime] = {}   # user_id → when candidate last wrote
_last_bot_msg:   dict[int, datetime] = {}   # user_id → when bot last replied
_user_step:      dict[int, str]      = {}   # user_id → current FSM step key
_user_name:      dict[int, str]      = {}   # user_id → display name
_notified:       set[int]            = set()  # already sent inactivity alert

_bot          = None
_channel_id:  int = 0
_admin_id:    int = 0


def init(bot, channel_id: int, admin_id: int) -> None:
    global _bot, _channel_id, _admin_id
    _bot        = bot
    _channel_id = channel_id
    _admin_id   = admin_id


def _display(user_id: int) -> str:
    name = _user_name.get(user_id, "")
    return name if name else f"ID:{user_id}"


async def log_incoming(user_id: int, username: str | None, text: str, step: str) -> None:
    """Called by middleware when a candidate sends any message."""
    now = datetime.utcnow()
    _last_cand_msg[user_id] = now
    _notified.discard(user_id)  # they responded — reset inactivity flag

    display = f"@{username}" if username else f"ID:{user_id}"
    _user_name[user_id] = display
    _user_step[user_id] = step

    if not _channel_id or not _bot:
        return

    label = _STEP_LABELS.get(step, step) if step and step != "—" else "Меню/старт"
    safe = text[:500].replace("<", "&lt;").replace(">", "&gt;")
    try:
        await _bot.send_message(
            _channel_id,
            f"📩 <b>{display}</b>  <code>{user_id}</code>\n"
            f"📍 <i>{label}</i>\n"
            f"└ {safe}",
            parse_mode="HTML",
            disable_notification=True,
        )
    except Exception as exc:
        logger.debug("live_feed.log_incoming: %s", exc)


async def log_outgoing(user_id: int, text: str) -> None:
    """Called by LoggingBot when bot sends a message to a candidate."""
    _last_bot_msg[user_id] = datetime.utcnow()

    if not _channel_id or not _bot:
        return

    name  = _display(user_id)
    step  = _user_step.get(user_id, "")
    label = _STEP_LABELS.get(step, step) if step else ""
    short = text[:300].replace("<", "&lt;").replace(">", "&gt;")
    if len(text) > 300:
        short += "…"

    try:
        await _bot.send_message(
            _channel_id,
            f"🤖 → <b>{name}</b>"
            + (f"  <i>{label}</i>" if label else "")
            + f"\n└ {short}",
            parse_mode="HTML",
            disable_notification=True,
        )
    except Exception as exc:
        logger.debug("live_feed.log_outgoing: %s", exc)


async def run_inactivity_checker(check_interval_min: int = 30, threshold_hours: int = 3) -> None:
    """Background task: alert admin when candidate stops responding for threshold_hours."""
    while True:
        await asyncio.sleep(check_interval_min * 60)
        if not _bot or not _admin_id:
            continue

        now = datetime.utcnow()
        for user_id, last_bot in list(_last_bot_msg.items()):
            if user_id in _notified:
                continue

            last_cand = _last_cand_msg.get(user_id, datetime.min)

            # Only alert if bot's last message is MORE recent (unanswered)
            if last_bot <= last_cand:
                continue

            silent_for = now - last_bot
            if silent_for < timedelta(hours=threshold_hours):
                continue

            name      = _display(user_id)
            step      = _user_step.get(user_id, "—")
            label     = _STEP_LABELS.get(step, step)
            hours_int = int(silent_for.total_seconds() // 3600)
            mins_int  = int((silent_for.total_seconds() % 3600) // 60)

            try:
                await _bot.send_message(
                    _admin_id,
                    f"⏰ <b>Кандидат не отвечает</b>\n\n"
                    f"👤 {name}  <code>{user_id}</code>\n"
                    f"📍 Шаг: <i>{label}</i>\n"
                    f"🕐 Молчит: <b>{hours_int}ч {mins_int}мин</b>\n"
                    f"📅 Бот писал в: {last_bot.strftime('%H:%M')} UTC",
                    parse_mode="HTML",
                )
                _notified.add(user_id)
            except Exception as exc:
                logger.debug("live_feed.inactivity_alert: %s", exc)
