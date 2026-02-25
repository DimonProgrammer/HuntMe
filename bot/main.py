"""HuntMe Recruitment Bot — entry point."""

import asyncio
import logging

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


async def main():
    logger.info("Starting HuntMe bot...")

    # Initialize database
    await init_db()
    logger.info("Database initialized")

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
