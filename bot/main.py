"""HuntMe Recruitment Bot — entry point."""

import asyncio
import logging
import os

from aiohttp import web
from aiogram import Bot, Dispatcher
from aiogram.fsm.storage.memory import MemoryStorage

from bot.config import config
from bot.database import init_db
from bot.handlers import admin, menu, operator_flow

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)


# Health-check HTTP server (keeps Render free tier awake)
async def health(_request):
    return web.Response(text="ok")


async def start_health_server():
    app = web.Application()
    app.router.add_get("/", health)
    app.router.add_get("/healthz", health)
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
    bot = Bot(token=config.BOT_TOKEN)
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
