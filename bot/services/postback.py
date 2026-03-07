"""Postback service — fire conversion events to external tracker (Keitaro/Binom/etc).

Usage:
    await fire_postback(click_id="abc123", event="qualified", payout=0)

The POSTBACK_URL env var is a template with placeholders: {click_id}, {status}, {payout}.
If POSTBACK_URL is empty, postbacks are silently skipped.
"""

import logging

import aiohttp

from bot.config import config

logger = logging.getLogger(__name__)


async def fire_postback(click_id: str, event: str, payout: float = 0) -> None:
    """Send GET postback to tracker. Non-blocking, errors are logged and swallowed."""
    if not click_id or not config.POSTBACK_URL:
        return

    url = config.POSTBACK_URL.format(
        click_id=click_id,
        status=event,
        payout=payout,
    )
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url, timeout=aiohttp.ClientTimeout(total=10)) as resp:
                logger.info("Postback %s → %s (click_id=%s)", event, resp.status, click_id)
    except Exception as exc:
        logger.warning("Postback failed for click_id=%s: %s", click_id, exc)
