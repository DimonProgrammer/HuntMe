"""AI client — supports Gemini (primary), OpenRouter (fallback), and Anthropic API.

Priority: Gemini (GEMINI_API_KEY) → OpenRouter (OPENROUTER_API_KEY) → Anthropic (CLAUDE_API_KEY).
Gemini 2.0 Flash is free (1500 req/day) and provides best quality for screening.
"""

import logging

import aiohttp

from bot.config import config

logger = logging.getLogger(__name__)


class AIClient:
    def __init__(self):
        if config.GEMINI_API_KEY:
            self.provider = "gemini"
            self.api_key = config.GEMINI_API_KEY
            # Gemini OpenAI-compatible endpoint
            self.base_url = "https://generativelanguage.googleapis.com/v1beta/openai"
            # gemini-2.0-flash: free, fast, high quality
            self.model = "gemini-2.0-flash"
        elif config.OPENROUTER_API_KEY:
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

        if self.provider in ("gemini", "openrouter"):
            return await self._openai_compat_complete(system, user_message, max_tokens)
        else:
            return await self._anthropic_complete(system, user_message, max_tokens)

    async def _openai_compat_complete(self, system: str, user_message: str, max_tokens: int) -> str:
        """Call any OpenAI-compatible API (Gemini or OpenRouter)."""
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        if self.provider == "openrouter":
            headers["HTTP-Referer"] = "https://apextalent.pro"
            headers["X-Title"] = "Apex Talent Bot"

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
                    logger.error("%s error %s: %s", self.provider, resp.status, data)
                    raise Exception(f"{self.provider} API error: {resp.status}")
                return data["choices"][0]["message"]["content"]

    async def _openrouter_complete(self, system: str, user_message: str, max_tokens: int) -> str:
        """Kept for compatibility — routes to _openai_compat_complete."""
        return await self._openai_compat_complete(system, user_message, max_tokens)

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
