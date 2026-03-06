"""Bitrix24 REST API client via incoming webhook."""
import logging
from typing import Any, Optional

import aiohttp

from wabot.config import config

logger = logging.getLogger(__name__)

# Bitrix24 CRM lead stages (map to pipeline stage IDs after setup)
STAGE_NEW = "NEW"
STAGE_ENGAGED = "IN_PROCESS"       # Вовлечён
STAGE_QUALIFIED = "PROCESSED"     # Квалифицирован
STAGE_INTERVIEW = "1"              # Интервью запланировано (custom stage ID, set after Bitrix setup)
STAGE_APPROVED = "WON"
STAGE_REJECTED = "LOSE"
STAGE_PAUSED = "JUNK"             # Пауза / не отвечает


async def _call(method: str, params: dict) -> Optional[Any]:
    if not config.BITRIX24_WEBHOOK_URL:
        logger.debug("Bitrix24 not configured, skipping %s", method)
        return None
    url = f"{config.BITRIX24_WEBHOOK_URL.rstrip('/')}/{method}"
    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(url, json=params, timeout=aiohttp.ClientTimeout(total=10)) as r:
                data = await r.json()
                if "error" in data:
                    logger.warning("Bitrix24 %s error: %s", method, data)
                    return None
                return data.get("result")
    except Exception as e:
        logger.error("Bitrix24 request failed %s: %s", method, e)
        return None


async def create_lead(phone: str, name: str = "", source: str = "wa_ad") -> Optional[int]:
    """Create a new CRM lead. Returns Bitrix24 lead ID."""
    result = await _call("crm.lead.add", {
        "fields": {
            "TITLE": f"WA Lead {phone}",
            "NAME": name or phone,
            "PHONE": [{"VALUE": phone, "VALUE_TYPE": "WORK"}],
            "SOURCE_ID": "WEB",
            "STATUS_ID": STAGE_NEW,
            "UF_CRM_WA_PHONE": phone,
            "UF_CRM_SOURCE": source,
        }
    })
    if result:
        logger.info("Bitrix24 lead created: %s → ID %s", phone, result)
        return int(result)
    return None


async def update_lead(
    lead_id: int,
    stage: Optional[str] = None,
    name: Optional[str] = None,
    fields: Optional[dict] = None,
) -> bool:
    """Update lead stage and/or custom fields."""
    update = fields or {}
    if stage:
        update["STATUS_ID"] = stage
    if name:
        update["NAME"] = name
    if not update:
        return True
    result = await _call("crm.lead.update", {"id": lead_id, "fields": update})
    return result is not None


async def set_step(lead_id: int, step: int):
    """Update funnel step field."""
    await update_lead(lead_id, fields={"UF_CRM_FUNNEL_STEP": str(step)})


async def add_note(lead_id: int, text: str):
    """Add a timeline note to the lead."""
    await _call("crm.timeline.comment.add", {
        "fields": {
            "ENTITY_ID": lead_id,
            "ENTITY_TYPE": "lead",
            "COMMENT": text,
        }
    })


async def add_followup_task(lead_id: int, title: str, hours_from_now: float):
    """Create a CRM task linked to lead for follow-up tracking."""
    from datetime import datetime, timedelta, timezone
    deadline = datetime.now(timezone.utc) + timedelta(hours=hours_from_now)
    await _call("tasks.task.add", {
        "fields": {
            "TITLE": title,
            "UF_CRM_TASK": [f"L_{lead_id}"],
            "DEADLINE": deadline.strftime("%Y-%m-%dT%H:%M:%S+00:00"),
        }
    })
