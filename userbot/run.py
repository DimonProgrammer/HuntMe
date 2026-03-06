"""Entry point for the HuntMe userbot.

Run with:
    python -m userbot.run

First launch will ask for your phone number and the OTP code from Telegram.
After that, a session file is saved and the bot runs without prompts.

The checker loop runs every 10 minutes and executes all outreach tasks.
"""

import asyncio
import logging
import sys
from pathlib import Path

# Add project root to path so 'bot' package imports work
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from dotenv import load_dotenv
load_dotenv()

from bot.database import init_db
from userbot.client import get_client
from userbot.tasks import (
    agent_reengagement,
    agent_welcome,
    interview_booked_followup,
    interview_noshow_followup,
)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)

_CHECK_INTERVAL_SEC = 10 * 60  # 10 minutes


async def run_all_tasks(client):
    """Run all outreach tasks in sequence."""
    logger.info("Running outreach tasks...")
    await interview_booked_followup(client)
    await interview_noshow_followup(client)
    await agent_welcome(client)
    await agent_reengagement(client)
    logger.info("All tasks done.")


async def main():
    logger.info("Initializing database...")
    await init_db()

    client = get_client()
    logger.info("Connecting to Telegram...")
    await client.start()
    logger.info("Userbot started as: %s", await client.get_me())

    # Run immediately on start, then loop
    await run_all_tasks(client)

    while True:
        await asyncio.sleep(_CHECK_INTERVAL_SEC)
        try:
            await run_all_tasks(client)
        except Exception:
            logger.exception("Task run failed")


if __name__ == "__main__":
    asyncio.run(main())
