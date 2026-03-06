"""Telethon client factory for the HuntMe userbot.

Session file is stored at ./userbot_session.session (git-ignored).
First run will prompt for phone number and OTP.
"""

import os
from pathlib import Path

from dotenv import load_dotenv
from telethon import TelegramClient
from telethon.sessions import StringSession

load_dotenv()

_API_ID = int(os.getenv("TG_API_ID", "0"))
_API_HASH = os.getenv("TG_API_HASH", "")

# Session file lives in project root so it's easy to find
_SESSION_PATH = str(Path(__file__).resolve().parent.parent / "userbot_session")


def get_client() -> TelegramClient:
    """Return a configured (not yet started) TelegramClient."""
    if not _API_ID or not _API_HASH:
        raise RuntimeError(
            "TG_API_ID and TG_API_HASH must be set in .env\n"
            "Get them at https://my.telegram.org → API development tools"
        )
    return TelegramClient(_SESSION_PATH, _API_ID, _API_HASH)
