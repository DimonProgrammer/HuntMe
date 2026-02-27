"""HuntMe Recruitment Bot — entry point."""

import asyncio
import json
import logging
import os
import re
from typing import Optional

from aiohttp import web
from aiogram import BaseMiddleware, Bot, Dispatcher
from bot.services.pg_storage import PostgresStorage
from aiogram.types import CallbackQuery, Message, TelegramObject

from bot.config import config
from bot.database import init_db
from bot.database.connection import async_session
from bot.database.models import Candidate
from sqlalchemy import select
from bot.handlers import admin, interview_booking, menu, operator_flow
from bot.services import live_feed
from bot.services import reminder
from bot.services import chatwoot_client

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)

# Global bot reference (set in main(), used by webhook handlers)
_bot: Optional[Bot] = None


# ── Live-feed: log every outgoing message ───────────────────────────────────
class LoggingBot(Bot):
    """Subclasses Bot to mirror outgoing messages to the live feed channel."""

    async def send_message(self, chat_id, text="", **kwargs):  # type: ignore[override]
        result = await super().send_message(chat_id, text, **kwargs)
        cid = int(chat_id)
        skip = {config.ADMIN_CHAT_ID, config.LIVE_FEED_CHANNEL_ID}
        if text and cid not in skip:
            asyncio.create_task(live_feed.log_outgoing(cid, str(text)))
            asyncio.create_task(chatwoot_client.mirror_outgoing(cid, str(text)))
        return result


# ── Live-feed: log every incoming message + button press ──────────────────
class LiveFeedMiddleware(BaseMiddleware):
    async def __call__(self, handler, event: TelegramObject, data: dict):
        if isinstance(event, Message) and event.from_user:
            user  = event.from_user
            state = data.get("state")
            step  = "—"
            if state:
                current = await state.get_state()
                if current:
                    step = current.split(":")[-1]
            text = event.text or f"[{event.content_type}]"
            asyncio.create_task(
                live_feed.log_incoming(user.id, user.username, text, step)
            )
            name = user.full_name or user.username or str(user.id)
            asyncio.create_task(
                chatwoot_client.mirror_incoming(user.id, name, user.username, text, step)
            )
        elif isinstance(event, CallbackQuery) and event.from_user and event.data:
            user = event.from_user
            # Extract readable button text from the inline keyboard
            button_text = event.data
            if event.message and hasattr(event.message, "reply_markup") and event.message.reply_markup:
                for row in event.message.reply_markup.inline_keyboard:
                    for btn in row:
                        if btn.callback_data == event.data:
                            button_text = btn.text
                            break
            state = data.get("state")
            step = "—"
            if state:
                current = await state.get_state()
                if current:
                    step = current.split(":")[-1]
            asyncio.create_task(
                live_feed.log_incoming(user.id, user.username, f"🔘 {button_text}", step)
            )
            name = user.full_name or user.username or str(user.id)
            asyncio.create_task(
                chatwoot_client.mirror_incoming(user.id, name, user.username, f"🔘 {button_text}", step)
            )
        return await handler(event, data)


# Health-check HTTP server (keeps Render free tier awake)
async def health(_request):
    return web.Response(text="ok")


_CORS = {
    "Access-Control-Allow-Origin": "*",
    "Access-Control-Allow-Methods": "POST, OPTIONS",
    "Access-Control-Allow-Headers": "Content-Type",
}


def _contact_link(contact: str) -> str:
    """Return a clickable Telegram HTML link based on contact type."""
    c = contact.strip()
    if re.match(r'^\+?[\d\s\-().]{7,}$', c):
        digits = re.sub(r'\D', '', c)
        return f' — <a href="https://wa.me/{digits}">📲 WA</a>'
    if c.startswith('@'):
        username = c.lstrip('@')
        return f' — <a href="https://t.me/{username}">✈️ TG</a>'
    if '@' in c and '.' in c:
        return f' — <a href="mailto:{c}">📧 Email</a>'
    return ''


async def landing_options(_request):
    """CORS preflight for landing form."""
    return web.Response(headers=_CORS)


async def landing_webhook(request):
    """Save landing lead (name + telegram) and return candidate_id for deep link."""
    try:
        data = await request.json()
    except Exception:
        return web.Response(status=400, text="Bad request")

    name = data.get("name", "").strip()
    telegram = data.get("telegram", "").strip().lstrip("@")
    backup_contact = data.get("contact", "").strip()
    language = data.get("language", "en").strip() or "en"

    # Save to Neon database
    candidate_id = None
    try:
        async with async_session() as session:
            candidate = Candidate(
                name=name,
                contact_info=f"@{telegram}" if telegram else backup_contact,
                platform="landing",
                candidate_type="operator",
                status="pending_bot",
                language=language,
            )
            session.add(candidate)
            await session.commit()
            await session.refresh(candidate)
            candidate_id = candidate.id
    except Exception as exc:
        logger.error("Failed to save landing lead: %s", exc)

    # Notify admin — brief, full screening happens in bot
    if _bot:
        tg_link = f'<a href="https://t.me/{telegram}">@{telegram}</a>' if telegram else "—"
        backup_line = f"\n📱 Backup: {backup_contact}" if backup_contact else ""
        # Build deep link: land_ru_<id> for Russian, land_<id> for English
        dl_prefix = "land_ru_" if language == "ru" else "land_"
        deep = f"https://t.me/apextalent_bot?start={dl_prefix}{candidate_id}" if candidate_id else ""
        lang_flag = "🇷🇺 RU" if language == "ru" else "🇬🇧 EN"
        admin_msg = (
            f"🌐 <b>Новый лид с сайта</b>\n\n"
            f"👤 <b>Имя:</b> {name or '—'}\n"
            f"✈️ <b>Telegram:</b> {tg_link}{backup_line}\n"
            f"🌍 <b>Язык:</b> {lang_flag}\n"
            f"🆔 #{candidate_id or '?'}\n\n"
            f"⏳ Ждём в боте для скрининга"
        )
        if deep:
            admin_msg += f"\n🔗 <a href=\"{deep}\">Deep link</a>"
        try:
            await _bot.send_message(config.ADMIN_CHAT_ID, admin_msg, parse_mode="HTML")
        except Exception as exc:
            logger.error("Failed to notify admin about landing lead: %s", exc)

        # Schedule reminder if lead doesn't enter bot within 30 min
        if candidate_id:
            asyncio.get_event_loop().call_later(
                1800,  # 30 minutes
                lambda cid=candidate_id, n=name, tg=tg_link: asyncio.ensure_future(
                    _check_landing_lead_entered_bot(cid, n, tg)
                ),
            )

    resp = {"ok": True}
    if candidate_id:
        resp["id"] = candidate_id
    return web.Response(
        text=json.dumps(resp),
        content_type="application/json",
        headers=_CORS,
    )


async def _check_landing_lead_entered_bot(candidate_id: int, name: str, tg_link: str):
    """Remind admin if a landing lead hasn't started the bot flow after 30 min."""
    try:
        async with async_session() as session:
            result = await session.execute(
                select(Candidate).where(Candidate.id == candidate_id)
            )
            candidate = result.scalar_one_or_none()
            if candidate and candidate.status == "pending_bot":
                msg = (
                    f"⚠️ <b>Лид #{candidate_id} не зашёл в бота</b>\n\n"
                    f"👤 {name} — {tg_link}\n"
                    f"Прошло 30 мин. Свяжитесь вручную."
                )
                await _bot.send_message(config.ADMIN_CHAT_ID, msg, parse_mode="HTML")
    except Exception as exc:
        logger.error("Landing lead check failed: %s", exc)


async def chatwoot_webhook(request):
    """Receive Chatwoot events; forward agent replies back to candidate in Telegram."""
    try:
        payload = await request.json()
    except Exception:
        return web.Response(status=400, text="Bad JSON")

    # Only handle new outgoing messages (agent → customer)
    if payload.get("event") != "message_created":
        return web.Response(text="ok")

    # message_type: 1 = outgoing (agent to customer), 0 = incoming
    msg_type = payload.get("message_type")
    if msg_type not in (1, "outgoing"):
        return web.Response(text="ok")

    content = (payload.get("content") or "").strip()
    if not content:
        return web.Response(text="ok")

    # Skip echo: messages created by our bot agent (avoid loop)
    sender = payload.get("sender") or {}
    sender_id = sender.get("id")
    if config.CHATWOOT_BOT_AGENT_ID and sender_id == config.CHATWOOT_BOT_AGENT_ID:
        return web.Response(text="ok")

    # Look up Telegram user from conversation_id
    conv_id = (payload.get("conversation") or {}).get("id")
    if not conv_id:
        return web.Response(text="ok")

    tg_user_id = await chatwoot_client.conversation_to_tg_user(conv_id)
    if not tg_user_id or not _bot:
        return web.Response(text="ok")

    try:
        await _bot.send_message(tg_user_id, content)
        logger.info("Chatwoot reply forwarded to TG user %s", tg_user_id)
    except Exception as exc:
        logger.warning("Failed to forward Chatwoot reply to %s: %s", tg_user_id, exc)

    return web.Response(text="ok")


async def start_health_server():
    app = web.Application()
    app.router.add_get("/", health)
    app.router.add_get("/healthz", health)
    app.router.add_post("/webhook/landing", landing_webhook)
    app.router.add_route("OPTIONS", "/webhook/landing", landing_options)
    app.router.add_post("/webhook/chatwoot", chatwoot_webhook)
    port = int(os.getenv("PORT", "10000"))
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, "0.0.0.0", port)
    await site.start()
    logger.info("Health-check server on port %s", port)


async def main():
    logger.info("Starting HuntMe bot...")

    # Initialize database
    await init_db()
    logger.info("Database initialized")

    # Start health-check server (for Render)
    await start_health_server()

    # Create bot and dispatcher
    global _bot
    bot = LoggingBot(token=config.BOT_TOKEN)
    _bot = bot
    dp = Dispatcher(storage=PostgresStorage())

    # Live feed: init service + register incoming-message middleware
    live_feed.init(bot, channel_id=config.LIVE_FEED_CHANNEL_ID, admin_id=config.ADMIN_CHAT_ID)
    if config.LIVE_FEED_CHANNEL_ID:
        _lf_mw = LiveFeedMiddleware()
        dp.message.outer_middleware(_lf_mw)
        dp.callback_query.outer_middleware(_lf_mw)
        asyncio.create_task(live_feed.run_inactivity_checker())
        logger.info("Live feed enabled → channel %s", config.LIVE_FEED_CHANNEL_ID)
    else:
        logger.info("Live feed disabled (LIVE_FEED_CHANNEL_ID not set)")

    # Register routers (order matters):
    # admin first — so admin commands + reply handler take priority
    # interview_booking — CRM booking FSM states
    # menu — handles /start, /menu, info pages, back_main
    # operator flow last — handles FSM states only
    dp.include_router(admin.router)
    dp.include_router(interview_booking.router)
    dp.include_router(menu.router)
    dp.include_router(operator_flow.router)

    # Background tasks
    asyncio.create_task(reminder.run_reminder_checker(bot))
    asyncio.create_task(reminder.run_interview_reminder_checker(bot))
    logger.info("Reminder checkers started")

    # Set Telegram command menu (blue button near keyboard)
    from aiogram.types import BotCommand
    await bot.set_my_commands([
        BotCommand(command="start", description="Start / Main menu"),
        BotCommand(command="ask", description="Ask a question"),
        BotCommand(command="menu", description="Back to main menu"),
    ])
    logger.info("Bot commands registered")

    logger.info("Bot is running. Admin ID: %s", config.ADMIN_CHAT_ID)

    try:
        await dp.start_polling(bot)
    finally:
        await bot.session.close()


if __name__ == "__main__":
    asyncio.run(main())
