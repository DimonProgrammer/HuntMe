"""HuntMe CRM MCP Server.

Exposes 3 tools for Claude Desktop / Claude Code:
  - get_slots        → list available interview slots
  - book_candidate   → submit application to HuntMe CRM
  - check_crm        → verify connection + auth

Setup: see README.md
"""

import asyncio
import json
import logging
import os
import re
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Optional

import aiohttp
from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import CallToolResult, TextContent, Tool

# ── Load .env from parent directory (project root) ───────────────────────────
def _load_env():
    for candidate in [Path(__file__).parent / ".env", Path(__file__).parent.parent / ".env"]:
        if candidate.exists():
            with open(candidate) as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith("#") and "=" in line:
                        k, v = line.split("=", 1)
                        os.environ.setdefault(k.strip(), v.strip().strip('"').strip("'"))
            break

_load_env()

CRM_BASE_URL  = os.getenv("HUNTME_CRM_BASE_URL", "https://app.huntme.pro").rstrip("/")
CRM_LOGIN     = os.getenv("HUNTME_CRM_LOGIN", "")
CRM_PASSWORD  = os.getenv("HUNTME_CRM_PASSWORD", "")

_USER_AGENT    = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36"
)
_SESSION_COOKIE = "__Secure-authjs.session-token"
_MANILA_TZ      = timezone(timedelta(hours=8))

_session_token: Optional[str] = None
_token_obtained_at: Optional[datetime] = None

logging.basicConfig(level=logging.WARNING)
logger = logging.getLogger("crm-mcp")


# ── Auth ──────────────────────────────────────────────────────────────────────

async def _login() -> Optional[str]:
    if not CRM_LOGIN or not CRM_PASSWORD:
        return None
    jar = aiohttp.CookieJar()
    headers = {"User-Agent": _USER_AGENT, "Accept": "application/json"}
    try:
        async with aiohttp.ClientSession(headers=headers, cookie_jar=jar) as session:
            async with session.get(
                f"{CRM_BASE_URL}/api/auth/csrf",
                timeout=aiohttp.ClientTimeout(total=15),
            ) as resp:
                if resp.status != 200:
                    return None
                csrf_token = (await resp.json()).get("csrfToken")
                if not csrf_token:
                    return None

            async with session.post(
                f"{CRM_BASE_URL}/api/auth/callback/credentials",
                data={
                    "csrfToken": csrf_token,
                    "login": CRM_LOGIN,
                    "password": CRM_PASSWORD,
                    "redirect": "false",
                    "callbackUrl": "/dashboard",
                    "json": "true",
                },
                timeout=aiohttp.ClientTimeout(total=15),
                allow_redirects=False,
            ) as resp:
                token = None
                for hv in resp.headers.getall("Set-Cookie", []):
                    m = re.search(r"__Secure-authjs\.session-token=([^;]+)", hv)
                    if m:
                        token = m.group(1)
                        break
                if not token:
                    for cookie in jar:
                        if cookie.key == _SESSION_COOKIE:
                            token = cookie.value
                            break
                return token
    except Exception as e:
        logger.warning("CRM login failed: %s", e)
        return None


async def _ensure_token() -> Optional[str]:
    global _session_token, _token_obtained_at
    if _session_token and _token_obtained_at:
        if datetime.now(timezone.utc) - _token_obtained_at < timedelta(hours=24):
            return _session_token
    token = await _login()
    if token:
        _session_token = token
        _token_obtained_at = datetime.now(timezone.utc)
    return token


# ── CRM requests ─────────────────────────────────────────────────────────────

async def _get(path: str, **params) -> Optional[dict]:
    global _session_token, _token_obtained_at
    token = await _ensure_token()
    if not token:
        return None
    headers = {"User-Agent": _USER_AGENT, "Accept": "application/json"}
    cookies = {_SESSION_COOKIE: token}
    try:
        async with aiohttp.ClientSession(headers=headers, cookies=cookies) as session:
            async with session.get(
                f"{CRM_BASE_URL}{path}",
                params=params,
                timeout=aiohttp.ClientTimeout(total=20),
            ) as resp:
                if resp.status in (401, 403):
                    _session_token = None
                    _token_obtained_at = None
                    return None
                if resp.status != 200:
                    return None
                return await resp.json()
    except Exception as e:
        logger.warning("CRM GET %s failed: %s", path, e)
        return None


# ── Tools logic ───────────────────────────────────────────────────────────────

async def tool_check_crm() -> str:
    if not CRM_LOGIN:
        return "❌ HUNTME_CRM_LOGIN not set in .env"
    token = await _login()
    if not token:
        return "❌ Login failed — check credentials"

    global _session_token, _token_obtained_at
    _session_token = token
    _token_obtained_at = datetime.now(timezone.utc)

    data = await _get(
        "/api/backend/interview-appointments/available-dates",
        office_id=95,
        funnel_key="operators",
    )
    if not data:
        return "⚠️ Login OK but slots fetch failed"

    slots = data.get("data") or {}
    total = sum(len(v) for v in slots.values())
    return f"✅ Connected. {len(slots)} days, {total} slots available."


async def tool_get_slots(count: int = 10) -> str:
    data = await _get(
        "/api/backend/interview-appointments/available-dates",
        office_id=95,
        funnel_key="operators",
    )
    if not data:
        return "❌ Failed to fetch slots — run check_crm to diagnose"

    slots = data.get("data") or {}
    now = datetime.now(_MANILA_TZ)
    cutoff = now + timedelta(hours=2)

    all_slots = []
    for date_str, times in slots.items():
        try:
            dt_day = datetime.strptime(date_str, "%d.%m.%Y")
            if dt_day.weekday() == 6:  # skip Sundays
                continue
        except ValueError:
            continue
        for time_str in times:
            try:
                dt = datetime.strptime(f"{date_str} {time_str}", "%d.%m.%Y %H:%M")
                dt = dt.replace(tzinfo=_MANILA_TZ)
                if dt > cutoff:
                    all_slots.append(dt)
            except ValueError:
                continue

    all_slots.sort()
    nearest = all_slots[:count]

    if not nearest:
        return "No available slots found."

    lines = ["Available interview slots (Manila time, GMT+8):\n"]
    for dt in nearest:
        lines.append(f"  • {dt.strftime('%a %d %b')} at {dt.strftime('%H:%M')}  →  {dt.strftime('%d.%m.%Y %H:%M')}")
    lines.append(f"\nUse the dd.MM.yyyy HH:mm format when booking.")
    return "\n".join(lines)


async def tool_book_candidate(
    name: str,
    birth_date: str,
    phone: str,
    telegram: str,
    slot: str,
    english_level: str = "B1 Intermediate",
    experience: str = "No prior experience",
    additional_notes: str = "",
) -> str:
    token = await _ensure_token()
    if not token:
        return "❌ CRM authentication failed"

    # Normalise phone
    digits = re.sub(r"\D", "", phone)
    country = "ph"
    if digits.startswith("63"):   country = "ph"
    elif digits.startswith("62"): country = "id"
    elif digits.startswith("234"):country = "ng"

    # Strip @ from telegram
    tg = telegram.lstrip("@")

    form_data = aiohttp.FormData()
    form_data.add_field("category", "0")
    form_data.add_field("office_id", "95")
    form_data.add_field("interview_appointment_date", slot)
    form_data.add_field("name", name)
    form_data.add_field("birth_date", birth_date)
    form_data.add_field("number", digits)
    form_data.add_field("phone_country", country)
    form_data.add_field("telegram", tg)
    form_data.add_field("questions_and_answers.0.question_id", "49")
    form_data.add_field("questions_and_answers.0.answer_text", "Apex Talent")
    form_data.add_field("questions_and_answers.1.question_id", "50")
    form_data.add_field("questions_and_answers.1.answer_text", english_level)
    form_data.add_field("questions_and_answers.2.question_id", "51")
    form_data.add_field("questions_and_answers.2.answer_text", experience[:200])
    form_data.add_field("questions_and_answers.3.question_id", "52")
    form_data.add_field("questions_and_answers.3.answer_text", additional_notes[:300])

    headers = {"User-Agent": _USER_AGENT}
    cookies = {_SESSION_COOKIE: token}

    try:
        async with aiohttp.ClientSession(headers=headers, cookies=cookies) as session:
            async with session.post(
                f"{CRM_BASE_URL}/api/backend/requests/create/operator",
                data=form_data,
                timeout=aiohttp.ClientTimeout(total=20),
            ) as resp:
                if resp.status in (200, 201):
                    try:
                        dt = datetime.strptime(slot, "%d.%m.%Y %H:%M")
                        display = dt.strftime("%a, %b %d at %H:%M")
                    except ValueError:
                        display = slot
                    return (
                        f"✅ Application submitted!\n\n"
                        f"Candidate: {name}\n"
                        f"Slot: {display} (Manila time)\n"
                        f"Telegram: @{tg}\n"
                        f"Phone: {digits} ({country.upper()})"
                    )
                text = await resp.text()
                return f"❌ CRM error {resp.status}: {text[:200]}"
    except Exception as e:
        return f"❌ Request failed: {e}"


# ── MCP Server ────────────────────────────────────────────────────────────────

server = Server("huntme-crm")


@server.list_tools()
async def list_tools() -> list[Tool]:
    return [
        Tool(
            name="check_crm",
            description="Test connection to HuntMe CRM — verify login and count available slots.",
            inputSchema={"type": "object", "properties": {}, "required": []},
        ),
        Tool(
            name="get_slots",
            description=(
                "Fetch available interview slots from HuntMe CRM. "
                "Returns a list of nearest available times in Manila timezone (GMT+8). "
                "Slots are in dd.MM.yyyy HH:mm format for use with book_candidate."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "count": {
                        "type": "integer",
                        "description": "How many slots to return (default 10)",
                        "default": 10,
                    }
                },
                "required": [],
            },
        ),
        Tool(
            name="book_candidate",
            description=(
                "Submit a candidate application to HuntMe CRM and book an interview slot. "
                "Slot must be in dd.MM.yyyy HH:mm format (use get_slots to find available times)."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "name":             {"type": "string", "description": "Full name (e.g. Mark Joshua G Serrano)"},
                    "birth_date":       {"type": "string", "description": "Date of birth in dd.MM.yyyy format (e.g. 15.05.1998)"},
                    "phone":            {"type": "string", "description": "Phone number with country code (e.g. +639664469038)"},
                    "telegram":         {"type": "string", "description": "Telegram username without @ (e.g. markjoshua)"},
                    "slot":             {"type": "string", "description": "Interview slot in dd.MM.yyyy HH:mm format (e.g. 05.03.2026 18:00)"},
                    "english_level":    {"type": "string", "description": "English level (e.g. B2 Upper-Intermediate)", "default": "B1 Intermediate"},
                    "experience":       {"type": "string", "description": "Brief work/experience description", "default": "No prior experience"},
                    "additional_notes": {"type": "string", "description": "Any extra notes for the interviewer", "default": ""},
                },
                "required": ["name", "birth_date", "phone", "telegram", "slot"],
            },
        ),
    ]


@server.call_tool()
async def call_tool(name: str, arguments: dict[str, Any]) -> list[TextContent]:
    if name == "check_crm":
        result = await tool_check_crm()

    elif name == "get_slots":
        result = await tool_get_slots(count=arguments.get("count", 10))

    elif name == "book_candidate":
        result = await tool_book_candidate(
            name=arguments["name"],
            birth_date=arguments["birth_date"],
            phone=arguments["phone"],
            telegram=arguments["telegram"],
            slot=arguments["slot"],
            english_level=arguments.get("english_level", "B1 Intermediate"),
            experience=arguments.get("experience", "No prior experience"),
            additional_notes=arguments.get("additional_notes", ""),
        )
    else:
        result = f"Unknown tool: {name}"

    return [TextContent(type="text", text=result)]


async def main():
    async with stdio_server() as (read_stream, write_stream):
        await server.run(read_stream, write_stream, server.create_initialization_options())


if __name__ == "__main__":
    asyncio.run(main())
