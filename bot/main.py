"""HuntMe Recruitment Bot — entry point."""

import asyncio
import logging
import os
from typing import Optional

from aiohttp import web
from aiogram import Bot, Dispatcher
from aiogram.fsm.storage.memory import MemoryStorage

from bot.config import config
from bot.database import init_db
from bot.database.connection import async_session
from bot.database.models import Candidate
from bot.handlers import admin, menu, operator_flow

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)

# Global bot reference (set in main(), used by webhook handlers)
_bot: Optional[Bot] = None


# Health-check HTTP server (keeps Render free tier awake)
async def health(_request):
    return web.Response(text="ok")


_CORS = {
    "Access-Control-Allow-Origin": "*",
    "Access-Control-Allow-Methods": "POST, OPTIONS",
    "Access-Control-Allow-Headers": "Content-Type",
}


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

    # Notify admin via Telegram
    if _bot:
        msg = (
            f"🌐 <b>Новый лид с сайта!</b>\n\n"
            f"👤 <b>Имя:</b> {name or '—'}\n"
            f"📱 <b>Контакт:</b> {whatsapp or '—'}\n"
            f"🌍 <b>Страна:</b> {country or '—'}\n"
            f"🎂 <b>Возраст:</b> {age or '—'}\n"
            f"🇬🇧 <b>Английский:</b> {english or '—'}\n"
            f"💼 <b>Статус:</b> {work_status or '—'}\n"
            + (f"🆔 <b>ID в базе:</b> #{candidate_id}" if candidate_id else "")
        )
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
    bot = Bot(token=config.BOT_TOKEN)
    _bot = bot
    dp = Dispatcher(storage=MemoryStorage())

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
