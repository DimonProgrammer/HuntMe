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
from bot.handlers import admin, menu, operator_flow
from bot.services import live_feed

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


async def _score_lead(country: str, english: str, status: str) -> tuple:
    """Quick AI lead score. Returns (score_str, note) or (None, None)."""
    try:
        from bot.services.claude_client import claude
        prompt = (
            f"Rate this streaming operator applicant 1-10. JSON only.\n"
            f"Country: {country} | English: {english} | Status: {status}\n\n"
            f"Output: {{\"score\": 1-10, \"verdict\": \"HOT|WARM|COLD\", \"note\": \"max 8 words\"}}\n"
            f"HOT: Philippines/Indonesia/Nigeria + B2+ English. COLD: low English or unavailable."
        )
        raw = await claude.complete(
            system="Recruitment screener. Respond with valid JSON only.",
            user_message=prompt,
            max_tokens=80,
        )
        match = re.search(r'\{.*?\}', raw, re.DOTALL)
        if match:
            data = json.loads(match.group())
            score = data.get("score", 5)
            verdict = data.get("verdict", "WARM")
            note = data.get("note", "")
            emoji = {"HOT": "🔥", "WARM": "✅", "COLD": "❄️"}.get(verdict, "✅")
            return f"{emoji} {verdict} ({score}/10)", note
    except Exception as exc:
        logger.debug("AI scoring failed: %s", exc)
    return None, None


async def landing_options(_request):
    """CORS preflight for landing form."""
    return web.Response(headers=_CORS)


async def landing_webhook(request):
    """Save landing page lead to DB and notify admin."""
    try:
        data = await request.json()
    except Exception:
        return web.Response(status=400, text="Bad request")

    name = data.get("name", "").strip()
    whatsapp = data.get("contact", data.get("whatsapp", "")).strip()
    country = data.get("country", "").strip()
    age_raw = data.get("age", "")
    english = data.get("english", "").strip()
    work_status = data.get("status", "").strip()

    try:
        age = int(age_raw) if age_raw else None
    except (ValueError, TypeError):
        age = None

    # Save to Neon database
    candidate_id = None
    try:
        async with async_session() as session:
            candidate = Candidate(
                name=name,
                contact_info=whatsapp,
                region=country,
                age=age,
                english_level=english,
                study_status=work_status,
                platform="landing",
                candidate_type="operator",
                status="new",
            )
            session.add(candidate)
            await session.commit()
            await session.refresh(candidate)
            candidate_id = candidate.id
    except Exception as exc:
        logger.error("Failed to save landing lead: %s", exc)

    # AI scoring (best-effort)
    score_str, score_note = await _score_lead(country, english, work_status)

    # Notify admin via Telegram
    if _bot:
        msg = (
            f"🌐 <b>Новый лид с сайта!</b>\n\n"
            f"👤 <b>Имя:</b> {name or '—'}\n"
            f"📱 <b>Контакт:</b> {whatsapp or '—'}{_contact_link(whatsapp)}\n"
            f"🌍 <b>Страна:</b> {country or '—'}\n"
            f"🎂 <b>Возраст:</b> {age or '—'}\n"
            f"🇬🇧 <b>Английский:</b> {english or '—'}\n"
            f"💼 <b>Статус:</b> {work_status or '—'}\n"
        )
        if score_str:
            msg += f"🎯 <b>AI-скоринг:</b> {score_str}"
            if score_note:
                msg += f" — {score_note}"
            msg += "\n"
        msg += (f"🆔 <b>ID:</b> #{candidate_id}" if candidate_id else "")
        try:
            await _bot.send_message(config.ADMIN_CHAT_ID, msg, parse_mode="HTML")
        except Exception as exc:
            logger.error("Failed to notify admin about landing lead: %s", exc)

    return web.Response(
        text='{"ok":true}',
        content_type="application/json",
        headers=_CORS,
    )


async def start_health_server():
    app = web.Application()
    app.router.add_get("/", health)
    app.router.add_get("/healthz", health)
    app.router.add_post("/webhook/landing", landing_webhook)
    app.router.add_route("OPTIONS", "/webhook/landing", landing_options)
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
    # menu second — handles /start, /menu, info pages, back_main
    # operator flow last — handles FSM states only
    dp.include_router(admin.router)
    dp.include_router(menu.router)
    dp.include_router(operator_flow.router)

    logger.info("Bot is running. Admin ID: %s", config.ADMIN_CHAT_ID)

    try:
        await dp.start_polling(bot)
    finally:
        await bot.session.close()


if __name__ == "__main__":
    asyncio.run(main())
