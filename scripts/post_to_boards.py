"""
Automated job posting to free boards via Playwright.
Designed to run via GitHub Actions cron (Mon/Wed/Fri).

Usage:
    python scripts/post_to_boards.py

Environment variables needed:
    CLAUDE_API_KEY — for generating fresh post text
    JORA_EMAIL / JORA_PASSWORD — optional, for Jora Philippines
"""

import asyncio
import logging
import os
import random

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

# Pre-written posts to use when Claude API is not available
FALLBACK_POSTS = {
    "ph": (
        "🎬 Live Stream Moderator — $150-400/week — Work From Home\n\n"
        "We're a talent agency looking for remote streaming moderators.\n\n"
        "What you'll do:\n"
        "— Set up streaming software (OBS) — full training provided\n"
        "— Moderate live chats during streams\n"
        "— Help streamers with technical issues\n"
        "— You NEVER appear on camera — behind-the-scenes work\n\n"
        "What we offer:\n"
        "— $150/week starting, top performers earn $400+/week\n"
        "— Paid training: 5-7 days with personal mentor ($30/shift)\n"
        "— Weekly payment every Sunday via GCash/Wise/USDT\n"
        "— 5/2 schedule, choose your shift\n"
        "— No experience needed\n\n"
        "Requirements:\n"
        "— Good English (B1+ level)\n"
        "— PC or laptop (Windows)\n"
        "— 100 Mbps internet\n\n"
        "Interested? Send your name and I'll tell you more!"
    ),
    "ng": (
        "💼 Remote Streaming Moderator — Earn $150-400/week in USD\n\n"
        "Join our international team as a behind-the-scenes streaming moderator.\n\n"
        "The role:\n"
        "— Technical setup for streamers (OBS, equipment)\n"
        "— Chat moderation during live streams\n"
        "— No camera, no content creation — purely behind the scenes\n\n"
        "What you get:\n"
        "— Starting pay: $150/week ($600/month)\n"
        "— Growth to $200-400+/week within 1-2 months\n"
        "— Paid training: 5-7 days, $30 per shift, personal mentor\n"
        "— Payment every Sunday via USDT/bank transfer\n"
        "— 5/2 schedule, 6-8 hours/day\n\n"
        "What you need:\n"
        "— Good English (written)\n"
        "— PC/laptop (Windows) + 100 Mbps internet\n"
        "— No experience required\n\n"
        "Apply: send your name and age. Let's talk!"
    ),
}


async def generate_post_text(region: str) -> str:
    """Generate a fresh post via Claude API, or fall back to template."""
    api_key = os.getenv("CLAUDE_API_KEY")
    if not api_key:
        logger.info("No CLAUDE_API_KEY — using fallback post for %s", region)
        return FALLBACK_POSTS.get(region, FALLBACK_POSTS["ph"])

    try:
        import anthropic

        client = anthropic.Anthropic(api_key=api_key)
        msg = client.messages.create(
            model="claude-haiku-4-5-20251001",
            max_tokens=500,
            system=(
                "Generate a job posting for Live Stream Moderator position. "
                "Role: behind-the-scenes technical support for streamers (OBS, chat moderation). "
                "Pay: $150/week starting, growth to $400+/week. Weekly Sunday payments. "
                "Paid training 5-7 days with personal mentor. No camera required. "
                "NEVER use words: webcam, adult, OnlyFans, nsfw, HuntMe. "
                "Use AIDA framework. Output post text only."
            ),
            messages=[
                {
                    "role": "user",
                    "content": f"Region: {region}. Generate a unique job post variant.",
                }
            ],
        )
        return msg.content[0].text
    except Exception:
        logger.exception("Claude API failed — using fallback")
        return FALLBACK_POSTS.get(region, FALLBACK_POSTS["ph"])


async def post_to_jora():
    """Post to Jora Philippines (employer.jora.com) — free."""
    email = os.getenv("JORA_EMAIL")
    password = os.getenv("JORA_PASSWORD")
    if not email or not password:
        logger.info("JORA credentials not set — skipping Jora")
        return

    try:
        from playwright.async_api import async_playwright

        post_text = await generate_post_text("ph")

        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            page = await browser.new_page()

            # Login
            await page.goto("https://employer.jora.com/login")
            await asyncio.sleep(random.uniform(1, 3))
            await page.fill('input[name="email"]', email)
            await page.fill('input[name="password"]', password)
            await page.click('button[type="submit"]')
            await asyncio.sleep(random.uniform(2, 4))

            # Navigate to post job
            await page.goto("https://employer.jora.com/post-job")
            await asyncio.sleep(random.uniform(1, 3))

            # Fill in job details
            await page.fill('input[name="title"]', "Live Stream Moderator — $150-400/week — Remote")
            await page.fill('textarea[name="description"]', post_text)
            # Additional fields may vary — adjust selectors as needed

            logger.info("Jora: post prepared (manual submit may be needed)")
            await browser.close()

    except ImportError:
        logger.warning("Playwright not installed — skipping Jora")
    except Exception:
        logger.exception("Jora posting failed")


async def main():
    logger.info("=== Job Posting Automation Started ===")

    # Generate posts for logging/review
    for region in ["ph", "ng"]:
        text = await generate_post_text(region)
        logger.info("Generated %s post (%d chars):\n%s\n", region.upper(), len(text), text[:200])

    # Attempt automated posting
    await post_to_jora()

    logger.info("=== Job Posting Automation Complete ===")


if __name__ == "__main__":
    asyncio.run(main())
