"""WA Bot — FastAPI webhook handler for WAHA Plus events."""
import logging

import uvicorn
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse

from wabot.config import config
from wabot.database import init_db, async_session
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


if __name__ == "__main__":
    uvicorn.run("wabot.main:app", host="0.0.0.0", port=config.PORT, reload=False)
