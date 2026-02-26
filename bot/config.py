import os
import re
from dotenv import load_dotenv

load_dotenv()


def _fix_db_url(url: str) -> str:
    """Convert various PostgreSQL URL formats to asyncpg driver."""
    if url.startswith("postgres://"):
        url = url.replace("postgres://", "postgresql+asyncpg://", 1)
    elif url.startswith("postgresql://"):
        url = url.replace("postgresql://", "postgresql+asyncpg://", 1)
    # Strip params asyncpg doesn't understand (sslmode, channel_binding)
    url = re.sub(r'[?&](sslmode|channel_binding)=[^&]*', '', url)
    # Fix leftover '&' at start of query string
    url = url.replace('?&', '?')
    return url


class Config:
    BOT_TOKEN: str = os.getenv("BOT_TOKEN", "")
    ADMIN_CHAT_ID: int = int(os.getenv("ADMIN_CHAT_ID", "0"))

    CLAUDE_API_KEY: str = os.getenv("CLAUDE_API_KEY", "")
    CLAUDE_BASE_URL: str = os.getenv("CLAUDE_BASE_URL", "https://api.anthropic.com")

    OPENROUTER_API_KEY: str = os.getenv("OPENROUTER_API_KEY", "")
    OPENROUTER_MODEL: str = os.getenv("OPENROUTER_MODEL", "meta-llama/llama-3.1-8b-instruct:free")

    GEMINI_API_KEY: str = os.getenv("GEMINI_API_KEY", "")
    GROQ_API_KEY: str = os.getenv("GROQ_API_KEY", "")

    DATABASE_URL: str = _fix_db_url(os.getenv("DATABASE_URL", "sqlite+aiosqlite:///huntme.db"))

    N8N_WEBHOOK_URL: str = os.getenv("N8N_WEBHOOK_URL", "http://n8n:5678/webhook")

    REFERRAL_LINK: str = os.getenv("REFERRAL_LINK", "")


config = Config()
