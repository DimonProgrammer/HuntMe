from bot.services.claude_client import claude

SYSTEM_PROMPT = """\
You are an expert recruitment copywriter. Generate job postings for remote chat moderator positions.

Rules:
- NEVER use words: webcam, adult, OnlyFans, nsfw, 18+, sexy, intimate
- USE safe terms: Chat Moderator, Content Moderator, Live Chat Operator
- Follow the AIDA framework: Attention → Interest → Desire → Action
- Include specific benefits that matter to the target region
- Keep it concise but compelling
- Include a clear call-to-action at the end
- Output the post text only, no commentary"""

REGION_CONTEXT = {
    "ph": (
        "Target: Philippines. "
        "Emphasize: USD payment (via GCash/Wise/crypto), WFH, flexible hours, "
        "no experience needed, training provided. "
        "Tone: professional but friendly. Language: English."
    ),
    "ng": (
        "Target: Nigeria. "
        "Emphasize: Earn in USD (weekly payment via USDT/bank transfer), "
        "work from anywhere, no experience needed. "
        "Tone: energetic, opportunity-focused. Language: English."
    ),
    "latam": (
        "Target: Latin America (Brazil, Argentina, Colombia, Mexico). "
        "Emphasize: Earn $1000+/month in USD, work from home, flexible schedule, "
        "supportive team. For CONTENT CREATOR / MODEL role, not operator. "
        "Tone: empowering, aspirational. Language: English (will be translated)."
    ),
}


async def generate_post(region: str, variant: int = 1) -> str:
    context = REGION_CONTEXT.get(region, REGION_CONTEXT["ph"])
    prompt = (
        f"{context}\n\n"
        f"Generate variant #{variant} of a job posting. "
        f"Make it unique — different hook, structure, and angle from other variants."
    )
    return await claude.complete(system=SYSTEM_PROMPT, user_message=prompt, max_tokens=600)
