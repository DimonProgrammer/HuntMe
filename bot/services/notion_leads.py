"""Notion Leads integration — upsert candidates to Notion Leads database.

Called from:
- menu.py cmd_start → create record (Started)
- operator_flow.py process_name → update name + stage
- operator_flow.py process_age → update age + stage
- operator_flow.py process_english → update english + stage
- operator_flow.py process_contact → update all final data + status
"""

import logging
from datetime import datetime, timezone
from typing import Optional

import aiohttp

from bot.config import config

logger = logging.getLogger(__name__)

NOTION_API_URL = "https://api.notion.com/v1"
NOTION_VERSION = "2022-06-28"

# FSM state → human-readable stage label
STATE_LABELS = {
    "OperatorForm:waiting_name": "1 · Entering name",
    "OperatorForm:waiting_has_pc": "2 · PC check",
    "OperatorForm:waiting_no_pc_followup": "2 · No PC follow-up",
    "OperatorForm:waiting_age": "3 · Age",
    "OperatorForm:waiting_study_work": "4 · Study/work",
    "OperatorForm:waiting_english": "5 · English level",
    "OperatorForm:waiting_pc_confidence": "6 · PC confidence",
    "OperatorForm:waiting_cpu": "7 · CPU",
    "OperatorForm:waiting_cpu_simple_age": "7 · CPU (PC age)",
    "OperatorForm:waiting_cpu_simple_usage": "7 · CPU (usage)",
    "OperatorForm:waiting_gpu": "8 · GPU",
    "OperatorForm:waiting_gpu_simple_gaming": "8 · GPU (gaming)",
    "OperatorForm:waiting_internet": "9 · Internet speed",
    "OperatorForm:waiting_start_date": "10 · Start date",
    "OperatorForm:waiting_contact": "11 · Contact info",
    "completed": "✅ Completed",
}

UTM_TO_SOURCE = {
    "fb_ph": "Facebook",
    "fb_ng": "Facebook",
    "fb_id": "Facebook",
    "facebook": "Facebook",
    "jiji": "Jiji",
    "indeed": "Indeed",
    "landing": "Landing",
    "glints": "Other",
    "wellfound": "Other",
}

RECOMMENDATION_TO_STATUS = {
    "PASS": "Qualified",
    "MAYBE": "In Progress",
    "REJECT": "Rejected",
}

ENGLISH_MAP = {
    "basic": "Basic",
    "conversational": "Conversational",
    "comfortable": "Comfortable",
    "fluent": "Fluent",
}


def _headers() -> dict:
    return {
        "Authorization": f"Bearer {config.NOTION_TOKEN}",
        "Notion-Version": NOTION_VERSION,
        "Content-Type": "application/json",
    }


def _rich_text(value: str) -> dict:
    return {"rich_text": [{"text": {"content": str(value)[:2000]}}]}


def _title(value: str) -> dict:
    return {"title": [{"text": {"content": str(value)[:2000]}}]}


def _select(value: str) -> dict:
    return {"select": {"name": value}}


def _date(dt: Optional[datetime] = None) -> dict:
    if dt is None:
        dt = datetime.now(timezone.utc)
    return {"date": {"start": dt.strftime("%Y-%m-%d")}}


async def _find_page_by_tg_id(tg_id: int) -> Optional[str]:
    """Query Notion DB for existing record with this TG ID. Returns page_id or None."""
    url = f"{NOTION_API_URL}/databases/{config.NOTION_LEADS_DB_ID}/query"
    payload = {
        "filter": {
            "property": "TG ID",
            "rich_text": {"equals": str(tg_id)},
        }
    }
    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(url, headers=_headers(), json=payload) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    results = data.get("results", [])
                    if results:
                        return results[0]["id"]
    except Exception:
        logger.debug("Notion query failed", exc_info=True)
    return None


async def _create_page(properties: dict) -> Optional[str]:
    """Create a new page in Notion Leads DB. Returns page_id."""
    url = f"{NOTION_API_URL}/pages"
    payload = {
        "parent": {"database_id": config.NOTION_LEADS_DB_ID},
        "properties": properties,
    }
    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(url, headers=_headers(), json=payload) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    return data["id"]
                else:
                    text = await resp.text()
                    logger.warning("Notion create failed %s: %s", resp.status, text[:300])
    except Exception:
        logger.debug("Notion create page failed", exc_info=True)
    return None


async def _update_page(page_id: str, properties: dict) -> None:
    """Patch existing Notion page."""
    url = f"{NOTION_API_URL}/pages/{page_id}"
    payload = {"properties": properties}
    try:
        async with aiohttp.ClientSession() as session:
            async with session.patch(url, headers=_headers(), json=payload) as resp:
                if resp.status != 200:
                    text = await resp.text()
                    logger.warning("Notion update failed %s: %s", resp.status, text[:300])
    except Exception:
        logger.debug("Notion update page failed", exc_info=True)


async def on_start(tg_id: int, tg_username: Optional[str], utm_source: Optional[str] = None) -> Optional[str]:
    """Called on /start. Creates or finds existing lead. Returns notion page_id."""
    if not config.NOTION_TOKEN or not config.NOTION_LEADS_DB_ID:
        return None

    source = UTM_TO_SOURCE.get(utm_source or "", "TG Bot")
    display_name = f"@{tg_username}" if tg_username else f"tg:{tg_id}"

    props = {
        "Name": _title(display_name),
        "TG ID": _rich_text(str(tg_id)),
        "TG Username": _rich_text(tg_username or ""),
        "Status": _select("Started"),
        "Stage": _rich_text("0 · Started bot"),
        "Source": _select(source),
        "Started At": _date(),
        "Updated At": _date(),
    }

    existing = await _find_page_by_tg_id(tg_id)
    if existing:
        # Don't reset status if already further in funnel
        props.pop("Status", None)
        props.pop("Started At", None)
        await _update_page(existing, props)
        return existing

    return await _create_page(props)


async def on_step(page_id: Optional[str], stage: str, extra_props: Optional[dict] = None) -> None:
    """Update stage and any extra properties on an existing lead."""
    if not page_id or not config.NOTION_TOKEN:
        return

    label = STATE_LABELS.get(stage, stage)
    props = {
        "Stage": _rich_text(label),
        "Status": _select("In Progress"),
        "Updated At": _date(),
    }
    if extra_props:
        props.update(extra_props)

    await _update_page(page_id, props)


async def on_name(page_id: Optional[str], full_name: str) -> None:
    await on_step(page_id, "OperatorForm:waiting_has_pc", {
        "Name": _title(full_name),
        "Full Name": _rich_text(full_name),
    })


async def on_age(page_id: Optional[str], age: int) -> None:
    await on_step(page_id, "OperatorForm:waiting_study_work", {
        "Age": {"number": age},
    })


async def on_english(page_id: Optional[str], english_level: str) -> None:
    mapped = ENGLISH_MAP.get(english_level.lower(), None)
    props = {}
    if mapped:
        props["English Level"] = _select(mapped)
    await on_step(page_id, "OperatorForm:waiting_pc_confidence", props)


async def on_has_pc(page_id: Optional[str], has_pc: bool) -> None:
    await on_step(page_id, "OperatorForm:waiting_age", {
        "Has PC": {"checkbox": has_pc},
    })


async def on_complete(
    page_id: Optional[str],
    tg_id: int,
    tg_username: Optional[str],
    data: dict,
    recommendation: str,
    score: Optional[float],
    notes: Optional[str],
) -> None:
    """Called after AI screening completes. Updates all collected data + final status."""
    if not config.NOTION_TOKEN:
        return

    if not page_id:
        page_id = await _find_page_by_tg_id(tg_id)

    if not page_id:
        return

    status = RECOMMENDATION_TO_STATUS.get(recommendation, "In Progress")
    full_name = data.get("name", "")
    english_raw = data.get("english_level", "")
    english_mapped = ENGLISH_MAP.get(english_raw.lower() if english_raw else "", None)
    contact = data.get("contact_info") or data.get("contact") or ""
    utm = data.get("utm_source", "")
    source = UTM_TO_SOURCE.get(utm or "", "TG Bot")

    props = {
        "Status": _select(status),
        "Stage": _rich_text(STATE_LABELS["completed"]),
        "Full Name": _rich_text(full_name),
        "Contact": _rich_text(contact),
        "Source": _select(source),
        "Updated At": _date(),
    }

    age = data.get("age")
    if age is not None:
        try:
            props["Age"] = {"number": int(age)}
        except (ValueError, TypeError):
            pass

    has_pc = data.get("has_pc")
    if has_pc is not None:
        props["Has PC"] = {"checkbox": bool(has_pc)}

    if english_mapped:
        props["English Level"] = _select(english_mapped)

    if score is not None:
        props["AI Score"] = {"number": round(score)}

    if notes:
        props["Notes"] = _rich_text(f"[{recommendation}] {notes}"[:2000])

    if tg_username:
        props["Name"] = _title(full_name or f"@{tg_username}")
        props["TG Username"] = _rich_text(tg_username)

    await _update_page(page_id, props)
