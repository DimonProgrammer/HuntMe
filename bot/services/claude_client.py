import anthropic

from bot.config import config


class ClaudeClient:
    def __init__(self):
        self.client = anthropic.AsyncAnthropic(
            api_key=config.CLAUDE_API_KEY,
            base_url=config.CLAUDE_BASE_URL,
        )
        self.model = "claude-haiku-4-5-20251001"

    async def complete(self, system: str, user_message: str, max_tokens: int = 1024) -> str:
        message = await self.client.messages.create(
            model=self.model,
            max_tokens=max_tokens,
            system=system,
            messages=[{"role": "user", "content": user_message}],
        )
        return message.content[0].text


claude = ClaudeClient()
