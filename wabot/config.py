import os
import re

from dotenv import load_dotenv

load_dotenv()


def _fix_db_url(url: str) -> str:
    if url.startswith("postgres://"):
        url = url.replace("postgres://", "postgresql+asyncpg://", 1)
    elif url.startswith("postgresql://"):
        url = url.replace("postgresql://", "postgresql+asyncpg://", 1)
    url = re.sub(r'[?&](sslmode|channel_binding)=[^&]*', '', url)
    url = url.replace('?&', '?')
    return url


class Config:
    # WAHA
    WAHA_URL: str = os.getenv("WAHA_URL", "http://localhost:3000")
    WAHA_API_KEY: str = os.getenv("WAHA_API_KEY", "")
    WAHA_SESSION: str = os.getenv("WAHA_SESSION", "default")

    # Bitrix24
    BITRIX24_WEBHOOK_URL: str = os.getenv("BITRIX24_WEBHOOK_URL", "")

    # Groq AI
    GROQ_API_KEY: str = os.getenv("GROQ_API_KEY", "")
    GROQ_MODEL: str = os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile")

    # Database (shared Neon PostgreSQL)
    DATABASE_URL: str = _fix_db_url(os.getenv("DATABASE_URL", ""))

    # Telegram admin notifications (reuse existing bot)
    BOT_TOKEN: str = os.getenv("BOT_TOKEN", "")
    ADMIN_CHAT_ID: int = int(os.getenv("ADMIN_CHAT_ID", "0"))

    # HuntMe CRM (interview booking)
    HUNTME_CRM_LOGIN: str = os.getenv("HUNTME_CRM_LOGIN", "")
    HUNTME_CRM_PASSWORD: str = os.getenv("HUNTME_CRM_PASSWORD", "")
    HUNTME_CRM_BASE_URL: str = os.getenv("HUNTME_CRM_BASE_URL", "https://huntmecrm.com")

    # Service
    PORT: int = int(os.getenv("WABOT_PORT", "8080"))
    WEBHOOK_SECRET: str = os.getenv("WEBHOOK_SECRET", "")


config = Config()
