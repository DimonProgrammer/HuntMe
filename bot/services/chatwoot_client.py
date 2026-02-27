"""Chatwoot API inbox integration.

Mirrors candidate ↔ bot conversations to Chatwoot for admin live monitoring.
Admin replies in Chatwoot UI → webhook → our bot forwards to candidate in Telegram.

Setup (Chatwoot side):
  1. Create an API inbox (Settings → Inboxes → Add Inbox → API)
  2. Set webhook URL to: https://apex-talent-bot.onrender.com/webhook/chatwoot
  3. Go to Profile → Access Token — copy your agent's API token
  4. Note down: Account ID (from URL /app/accounts/N/...), Inbox ID

Env vars needed:
  CHATWOOT_BASE_URL     — e.g. https://chat.apextalent.pro
  CHATWOOT_API_TOKEN    — agent API access token (Profile → Access Token)
  CHATWOOT_ACCOUNT_ID   — numeric account ID (from Chatwoot URL)
  CHATWOOT_INBOX_ID     — numeric inbox ID for the API inbox
  CHATWOOT_BOT_AGENT_ID — numeric ID of the agent whose token is used (prevents echo)
"""

from __future__ import annotations

import logging
from typing import Optional

import aiohttp

from bot.config import config
from bot.database.connection import async_session
from bot.database.models import ChatwootMapping

logger = logging.getLogger(__name__)

# Module-level persistent HTTP session
_http: Optional[aiohttp.ClientSession] = None


def _enabled() -> bool:
    return bool(config.CHATWOOT_BASE_URL and config.CHATWOOT_API_TOKEN and config.CHATWOOT_INBOX_ID)


def _headers() -> dict:
    return {
        "api_access_token": config.CHATWOOT_API_TOKEN,
        "Content-Type": "application/json",
    }


def _base() -> str:
    return f"{config.CHATWOOT_BASE_URL.rstrip('/')}/api/v1/accounts/{config.CHATWOOT_ACCOUNT_ID}"


async def _session() -> aiohttp.ClientSession:
    global _http
    if _http is None or _http.closed:
        _http = aiohttp.ClientSession()
    return _http


# ── Contact + Conversation management ──────────────────────────────────────────

async def get_or_create_conversation(
    tg_user_id: int, name: str, username: Optional[str] = None
) -> Optional[int]:
    """Return existing Chatwoot conversation_id or create a new contact+conversation."""
    # Check cached mapping in DB
    async with async_session() as session:
        mapping = await session.get(ChatwootMapping, tg_user_id)
        if mapping:
            return mapping.conversation_id

    contact_id = await _find_or_create_contact(tg_user_id, name, username)
    if not contact_id:
        return None

    conv_id = await _create_conversation(contact_id)
    if not conv_id:
        return None

    async with async_session() as session:
        session.add(ChatwootMapping(
            tg_user_id=tg_user_id,
            contact_id=contact_id,
            conversation_id=conv_id,
        ))
        await session.commit()

    logger.info("Chatwoot: new conversation %s for user %s", conv_id, tg_user_id)
    return conv_id


async def _find_or_create_contact(tg_user_id: int, name: str, username: Optional[str]) -> Optional[int]:
    s = await _session()
    url = f"{_base()}/contacts"
    identifier = str(tg_user_id)
    display = name or (f"@{username}" if username else f"TG:{tg_user_id}")
    payload = {
        "name": display,
        "identifier": identifier,
        "additional_attributes": {
            "telegram_id": tg_user_id,
            "telegram_username": username or "",
        },
    }
    try:
        async with s.post(url, json=payload, headers=_headers()) as resp:
            if resp.status in (200, 201):
                data = await resp.json()
                return data.get("id")
            if resp.status == 422:
                # Contact already exists — search by identifier
                return await _search_contact(identifier)
            logger.warning("Chatwoot create contact %s: HTTP %s", tg_user_id, resp.status)
    except Exception as exc:
        logger.error("Chatwoot create contact: %s", exc)
    return None


async def _search_contact(identifier: str) -> Optional[int]:
    s = await _session()
    url = f"{_base()}/contacts/search"
    try:
        async with s.get(url, params={"q": identifier}, headers=_headers()) as resp:
            if resp.status == 200:
                data = await resp.json()
                contacts = (data.get("payload") or {}).get("contacts") or data.get("payload") or []
                for c in contacts:
                    if str(c.get("identifier", "")) == identifier:
                        return c["id"]
    except Exception as exc:
        logger.error("Chatwoot search contact: %s", exc)
    return None


async def _create_conversation(contact_id: int) -> Optional[int]:
    s = await _session()
    url = f"{_base()}/conversations"
    payload = {
        "inbox_id": config.CHATWOOT_INBOX_ID,
        "contact_id": contact_id,
    }
    try:
        async with s.post(url, json=payload, headers=_headers()) as resp:
            if resp.status in (200, 201):
                data = await resp.json()
                return data.get("id")
            logger.warning("Chatwoot create conversation: HTTP %s", resp.status)
    except Exception as exc:
        logger.error("Chatwoot create conversation: %s", exc)
    return None


# ── Posting messages ────────────────────────────────────────────────────────────

async def _post_message(conversation_id: int, content: str, message_type: str = "incoming") -> None:
    s = await _session()
    url = f"{_base()}/conversations/{conversation_id}/messages"
    payload = {
        "content": content[:65535],
        "message_type": message_type,
        "private": False,
    }
    try:
        async with s.post(url, json=payload, headers=_headers()) as resp:
            if resp.status not in (200, 201):
                logger.debug("Chatwoot post_message %s: HTTP %s", conversation_id, resp.status)
    except Exception as exc:
        logger.debug("Chatwoot post_message: %s", exc)


async def mirror_incoming(
    tg_user_id: int, name: str, username: Optional[str], text: str, step: str = ""
) -> None:
    """Mirror a candidate's message to Chatwoot (shows as incoming from customer)."""
    if not _enabled():
        return
    try:
        conv_id = await get_or_create_conversation(tg_user_id, name, username)
        if not conv_id:
            return
        label = f"[{step}] " if step and step not in ("—", "") else ""
        await _post_message(conv_id, f"{label}{text}", "incoming")
    except Exception as exc:
        logger.debug("Chatwoot mirror_incoming: %s", exc)


async def mirror_outgoing(tg_user_id: int, text: str) -> None:
    """Mirror a bot message to Chatwoot (shows as outgoing from agent/bot)."""
    if not _enabled():
        return
    try:
        async with async_session() as session:
            mapping = await session.get(ChatwootMapping, tg_user_id)
            if not mapping:
                return
        await _post_message(mapping.conversation_id, text, "outgoing")
    except Exception as exc:
        logger.debug("Chatwoot mirror_outgoing: %s", exc)


# ── Webhook: admin reply → Telegram ────────────────────────────────────────────

async def conversation_to_tg_user(conversation_id: int) -> Optional[int]:
    """Look up tg_user_id for a Chatwoot conversation_id."""
    from sqlalchemy import select
    async with async_session() as session:
        result = await session.execute(
            select(ChatwootMapping).where(ChatwootMapping.conversation_id == conversation_id)
        )
        mapping = result.scalar_one_or_none()
        return mapping.tg_user_id if mapping else None
