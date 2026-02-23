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
        "🌐 Remote Chat Moderator — Work From Home — USD Payment\n\n"
        "We are hiring chat moderators for a growing international platform.\n\n"
        "Requirements:\n"
        "— Good written English\n"
        "— Reliable internet connection\n"
        "— 4+ hours daily availability\n"
        "— Laptop or PC\n"
        "— No experience needed — full training provided\n\n"
        "What we offer:\n"
        "— Work from home, flexible schedule\n"
        "— Payment in USD (weekly via GCash/Wise/crypto)\n"
        "— Long-term position with growth\n"
        "— Supportive team and ongoing training\n\n"
        "Interested? Send a short introduction about yourself."
    ),
    "ng": (
        "💼 Hiring: Online Chat Moderator — Earn in USD Weekly\n\n"
        "Join our international team as a remote chat moderator.\n\n"
        "What you need:\n"
        "— Good English (written)\n"
        "— Stable internet\n"
        "— Computer or laptop\n"
        "— 4-8 hours per day\n\n"
        "What you get:\n"
        "— Weekly pay in USD (USDT/bank transfer)\n"
        "— Work from anywhere\n"
        "— Free training — no experience needed\n"
        "— Flexible hours\n\n"
        "Apply now: send your name, age, and a short message about yourself."
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
                "Generate a job posting for Remote Chat Moderator. "
                "NEVER use words: webcam, adult, OnlyFans, nsfw. "
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
            await page.fill('input[name="title"]', "Remote Chat Moderator — USD Payment")
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
