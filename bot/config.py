import os
from dotenv import load_dotenv

load_dotenv()


class Config:
    BOT_TOKEN: str = os.getenv("BOT_TOKEN", "")
    ADMIN_CHAT_ID: int = int(os.getenv("ADMIN_CHAT_ID", "0"))

    CLAUDE_API_KEY: str = os.getenv("CLAUDE_API_KEY", "")
    CLAUDE_BASE_URL: str = os.getenv("CLAUDE_BASE_URL", "https://api.anthropic.com")

    FREEPIK_API_KEY: str = os.getenv("FREEPIK_API_KEY", "")

    DATABASE_URL: str = os.getenv(
        "DATABASE_URL",
        "postgresql+asyncpg://huntme:huntme_password@localhost:5432/huntme",
    )

    N8N_WEBHOOK_URL: str = os.getenv("N8N_WEBHOOK_URL", "http://n8n:5678/webhook")

    REFERRAL_LINK: str = os.getenv("REFERRAL_LINK", "")


config = Config()
