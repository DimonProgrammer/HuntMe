"""WA Bot — FastAPI webhook handler for WAHA Plus events."""
import logging
from datetime import datetime, timezone

import uvicorn
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from sqlalchemy import select

from wabot.config import config
from wabot.database import init_db, async_session
from wabot.models import WaLead
from wabot import fsm, scheduler

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(name)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)

app = FastAPI(title="Apex Talent WA Bot")


@app.on_event("startup")
async def startup():
    await init_db()
    scheduler.start()
    logger.info("WA Bot started on port %s", config.PORT)


@app.on_event("shutdown")
async def shutdown():
    scheduler.stop()


@app.get("/healthz")
async def health():
    return {"status": "ok"}


@app.post("/webhook/waha")
async def waha_webhook(request: Request):
    """Receive events from WAHA Plus."""
    # Optional: verify secret header
    if config.WEBHOOK_SECRET:
        secret = request.headers.get("X-Webhook-Secret", "")
        if secret != config.WEBHOOK_SECRET:
            raise HTTPException(status_code=401, detail="Unauthorized")

    try:
        event = await request.json()
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid JSON")

    event_type = event.get("event", "")

    # Only handle incoming messages
    if event_type != "message":
        return JSONResponse({"status": "ignored"})

    payload = event.get("payload", {})

    # Skip group messages, status updates, own messages
    chat_id: str = payload.get("from", "")
    if not chat_id or "@g.us" in chat_id or payload.get("fromMe", False):
        return JSONResponse({"status": "ignored"})

    # Extract phone (remove @c.us suffix)
    phone = "+" + chat_id.replace("@c.us", "")

    # Extract text
    body = payload.get("body", "").strip()
    if not body:
        return JSONResponse({"status": "no_text"})

    logger.info("Incoming WA message from %s: %s", phone, body[:50])

    async with async_session() as session:
        await fsm.process_message(session, phone, body)

    return JSONResponse({"status": "ok"})


# =====================================================================
# ADMIN API — retention & disqualification triggers
# =====================================================================

class DisqualifyRequest(BaseModel):
    phone: str
    reason: str = "generic"  # age | device | generic


class RetentionRequest(BaseModel):
    phone: str
    milestone: str  # booking_confirmed | post_interview | work_day_N | shift_7


class ShiftUpdateRequest(BaseModel):
    phone: str
    shifts: int


class InterviewDateRequest(BaseModel):
    phone: str
    interview_date: str  # ISO 8601 format


@app.post("/api/disqualify")
async def disqualify_model(req: DisqualifyRequest):
    """Disqualify a model candidate and offer agent role."""
    async with async_session() as session:
        result = await session.execute(select(WaLead).where(WaLead.phone == req.phone))
        lead = result.scalar_one_or_none()
        if not lead:
            raise HTTPException(status_code=404, detail="Lead not found")
        await fsm.offer_agent_role(lead, session, reason=req.reason)
    return {"status": "ok", "phone": req.phone, "reason": req.reason}


@app.post("/api/retention")
async def trigger_retention(req: RetentionRequest):
    """Trigger a retention message for a lead."""
    async with async_session() as session:
        await fsm.send_retention_message(session, req.phone, req.milestone)
    return {"status": "ok", "phone": req.phone, "milestone": req.milestone}


@app.post("/api/shifts")
async def update_shifts(req: ShiftUpdateRequest):
    """Update shift count for a working model (triggers retention automatically via scheduler)."""
    async with async_session() as session:
        result = await session.execute(select(WaLead).where(WaLead.phone == req.phone))
        lead = result.scalar_one_or_none()
        if not lead:
            raise HTTPException(status_code=404, detail="Lead not found")
        lead.shifts_completed = req.shifts
        await session.commit()
    return {"status": "ok", "phone": req.phone, "shifts": req.shifts}


@app.post("/api/interview-date")
async def set_interview_date(req: InterviewDateRequest):
    """Set interview date for a booked lead (enables retention scheduling)."""
    async with async_session() as session:
        result = await session.execute(select(WaLead).where(WaLead.phone == req.phone))
        lead = result.scalar_one_or_none()
        if not lead:
            raise HTTPException(status_code=404, detail="Lead not found")
        try:
            lead.interview_date = datetime.fromisoformat(req.interview_date).replace(tzinfo=timezone.utc)
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid date format. Use ISO 8601.")
        await session.commit()

    # Send booking confirmation retention message
    async with async_session() as session:
        await fsm.send_retention_message(session, req.phone, "booking_confirmed")

    return {"status": "ok", "phone": req.phone, "interview_date": req.interview_date}


if __name__ == "__main__":
    uvicorn.run("wabot.main:app", host="0.0.0.0", port=config.PORT, reload=False)
