"""AI client — supports OpenRouter (free tier) and Anthropic API.

Uses OpenRouter by default (OPENROUTER_API_KEY).
Falls back to Anthropic if CLAUDE_API_KEY is set.
"""

import logging

import aiohttp

from bot.config import config

logger = logging.getLogger(__name__)


class AIClient:
    def __init__(self):
        if config.OPENROUTER_API_KEY:
            self.provider = "openrouter"
            self.api_key = config.OPENROUTER_API_KEY
            self.base_url = "https://openrouter.ai/api/v1"
            self.model = config.OPENROUTER_MODEL or "meta-llama/llama-3.1-8b-instruct:free"
        elif config.CLAUDE_API_KEY:
            self.provider = "anthropic"
            self.api_key = config.CLAUDE_API_KEY
            self.base_url = config.CLAUDE_BASE_URL
            self.model = "claude-haiku-4-5-20251001"
        else:
            self.provider = "none"
            self.api_key = ""
            self.base_url = ""
            self.model = ""
            logger.warning("No AI API key configured — screening will use fallback")

    async def complete(self, system: str, user_message: str, max_tokens: int = 1024) -> str:
        if self.provider == "none":
            return '{"english_score":5,"hardware_score":5,"availability_score":5,"motivation_score":5,"experience_score":5,"overall_score":50,"recommendation":"MAYBE","reasoning":"AI screening unavailable — manual review needed","suggested_response":"Thank you for applying! Our team will review your application and get back to you within 24 hours."}'

        if self.provider == "openrouter":
            return await self._openrouter_complete(system, user_message, max_tokens)
        else:
            return await self._anthropic_complete(system, user_message, max_tokens)

    async def _openrouter_complete(self, system: str, user_message: str, max_tokens: int) -> str:
        """Call OpenRouter API (OpenAI-compatible)."""
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
            "HTTP-Referer": "https://apexhiring.vercel.app",
            "X-Title": "Apex Talent Bot",
        }
        payload = {
            "model": self.model,
            "max_tokens": max_tokens,
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": user_message},
            ],
        }
        async with aiohttp.ClientSession() as session:
            async with session.post(
                f"{self.base_url}/chat/completions",
                headers=headers,
                json=payload,
                timeout=aiohttp.ClientTimeout(total=30),
            ) as resp:
                data = await resp.json()
                if resp.status != 200:
                    logger.error("OpenRouter error %s: %s", resp.status, data)
                    raise Exception(f"OpenRouter API error: {resp.status}")
                return data["choices"][0]["message"]["content"]

    async def _anthropic_complete(self, system: str, user_message: str, max_tokens: int) -> str:
        """Call Anthropic API directly."""
        import anthropic
        client = anthropic.AsyncAnthropic(
            api_key=self.api_key,
            base_url=self.base_url,
        )
        message = await client.messages.create(
            model=self.model,
            max_tokens=max_tokens,
            system=system,
            messages=[{"role": "user", "content": user_message}],
        )
        return message.content[0].text


claude = AIClient()
