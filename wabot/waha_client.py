"""WAHA Plus REST API client."""
import asyncio
import logging
import random
from typing import Optional

import aiohttp

from wabot.config import config

logger = logging.getLogger(__name__)


def _headers() -> dict:
    return {"X-Api-Key": config.WAHA_API_KEY, "Content-Type": "application/json"}


def _chat_id(phone: str) -> str:
    """Convert +55... phone to WAHA chat ID format: 5511999...@c.us"""
    digits = phone.lstrip("+")
    return f"{digits}@c.us"


async def _post(path: str, payload: dict) -> Optional[dict]:
    url = f"{config.WAHA_URL}{path}"
    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(url, json=payload, headers=_headers(), timeout=aiohttp.ClientTimeout(total=15)) as r:
                if r.status not in (200, 201):
                    logger.warning("WAHA %s → %s: %s", path, r.status, await r.text())
                    return None
                return await r.json()
    except Exception as e:
        logger.error("WAHA request failed %s: %s", path, e)
        return None


async def _typing_pause(phone: str, seconds: float = 2.0):
    """Send typing indicator then wait."""
    chat = _chat_id(phone)
    await _post(f"/api/{config.WAHA_SESSION}/chats/{chat}/typing", {"duration": int(seconds * 1000)})
    await asyncio.sleep(seconds)


async def send_text(phone: str, text: str, delay: Optional[float] = None):
    """Send text message with optional typing indicator before."""
    if delay is None:
        # Natural delay: 1.5–3s, longer for longer messages
        delay = min(1.5 + len(text) / 200, 4.0) + random.uniform(0, 0.5)
    await _typing_pause(phone, delay)
    return await _post(f"/api/sendText", {
        "session": config.WAHA_SESSION,
        "chatId": _chat_id(phone),
        "text": text,
    })


async def send_image(phone: str, url: str, caption: str = ""):
    """Send image from URL."""
    await asyncio.sleep(random.uniform(1.0, 2.0))
    return await _post(f"/api/sendImage", {
        "session": config.WAHA_SESSION,
        "chatId": _chat_id(phone),
        "file": {"url": url},
        "caption": caption,
    })


async def send_audio(phone: str, url: str):
    """Send voice note (PTT) from URL."""
    await asyncio.sleep(random.uniform(1.0, 1.5))
    return await _post(f"/api/sendVoice", {
        "session": config.WAHA_SESSION,
        "chatId": _chat_id(phone),
        "file": {"url": url},
    })


async def send_messages(phone: str, messages: list[str], base_delay: float = 1.5):
    """Send a sequence of text messages with natural pauses between them."""
    for i, text in enumerate(messages):
        delay = base_delay if i > 0 else None
        await send_text(phone, text, delay=delay)
        if i < len(messages) - 1:
            await asyncio.sleep(random.uniform(0.5, 1.2))
