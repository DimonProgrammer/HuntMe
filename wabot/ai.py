"""Groq AI — free-text responses as Gabi avatar."""
import logging
from typing import Optional

import aiohttp

from wabot.config import config

logger = logging.getLogger(__name__)

GABI_SYSTEM_PROMPT = """Ты — Габи (Gabriela), 26 лет, из São Paulo interior.
Ты вербуешь девушек в проект цифрового развлечения Projeto Centelha.

Твой путь: была vendedora на R$1.800 → узнала о streaming entertainment →
через 3 месяца R$5K → через 6 месяцев в Дубай. Сейчас R$12K+/мес.

ПРАВИЛА:
- Пиши на PT-BR, разговорно, как подруга — НЕ как HR
- Короткие сообщения (1-3 предложения), без длинных объяснений
- Тёпло, с юмором, энергично — но не давить
- НЕ раскрывай детали раньше времени (progressive disclosure)
- Формат работы: "entretenimento digital / streaming"
- Если возражение — выслушай, прими, ответь через свой опыт
- Если офтоп / оскорбление — мягко верни к теме
- После ответа на вопрос — мягко подтолкни продолжить (написать "+")
"""


async def get_response(user_text: str, context: str = "", step: int = 0) -> Optional[str]:
    """Get Gabi's AI response to free-form user input."""
    if not config.GROQ_API_KEY:
        return None

    messages = [{"role": "system", "content": GABI_SYSTEM_PROMPT}]

    if context:
        messages.append({"role": "system", "content": f"Контекст диалога: {context}"})

    messages.append({"role": "user", "content": user_text})

    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(
                "https://api.groq.com/openai/v1/chat/completions",
                headers={"Authorization": f"Bearer {config.GROQ_API_KEY}", "Content-Type": "application/json"},
                json={
                    "model": config.GROQ_MODEL,
                    "messages": messages,
                    "max_tokens": 200,
                    "temperature": 0.8,
                },
                timeout=aiohttp.ClientTimeout(total=15),
            ) as r:
                if r.status != 200:
                    logger.warning("Groq API error: %s", r.status)
                    return None
                data = await r.json()
                return data["choices"][0]["message"]["content"].strip()
    except Exception as e:
        logger.error("Groq request failed: %s", e)
        return None
