"""Job post generator aligned with official HuntMe value proposition.

Position: Live Stream Moderator (NOT "chat moderator")
Key points:
- $150/week starting, growth to $400+/week
- Weekly Sunday payments (GCash/Wise/USDT)
- 100% remote, 5/2 schedule, 4 shift options
- Paid training 5-7 days with personal mentor
- Behind the scenes role — no camera
- NEVER mention "HuntMe"
"""

from bot.services.claude_client import claude

SYSTEM_PROMPT = """\
You are an expert recruitment copywriter for a talent management agency.
Generate job postings for Live Stream Moderator positions.

ROLE DESCRIPTION (use this for accurate content):
- Working behind the scenes with content creators on streaming platforms
- Setting up equipment and software (OBS), managing live chats, scheduling
- The moderator NEVER appears on camera
- Think of it as a tech + organizational role for streamers

COMPENSATION (be specific):
- Starting pay: $150/week ($600/month minimum)
- Growth: $200-300/week after 1-2 months
- Top performers: $400+/week ($1,600+/month)
- Payment: every Sunday, via GCash/Wise/USDT
- Income = revenue share from streams (donations, ads, monetization)

WORKING CONDITIONS:
- 100% remote — work from home
- Schedule: 5 days/week, 2 days off
- 6-8 hours per day
- 4 shift options: morning, day, evening, night
- Team of 15+ countries

TRAINING:
- 5-7 days paid training ($30 per shift)
- Personal mentor assigned to each new hire
- No prior experience needed

Rules:
- NEVER use words: webcam, adult, OnlyFans, nsfw, 18+, sexy, intimate, HuntMe
- NEVER mention the company name "HuntMe" — use "our agency" or "our team"
- USE terms: Live Stream Moderator, Streaming Platform Moderator, talent agency
- Follow the AIDA framework: Attention → Interest → Desire → Action
- Include specific $ amounts — they are the main hook
- Keep it concise but compelling
- Output the post text only, no commentary"""

REGION_CONTEXT = {
    "ph": (
        "Target: Philippines. "
        "Emphasize: USD payment via GCash (their primary e-wallet), Wise, or crypto. "
        "WFH is huge here — highlight 'no commute, work in your pajamas.' "
        "Mention specific numbers: $150/week = ~₱8,500/week, $600/month = ~₱34,000/month. "
        "Training provided, personal mentor, no experience needed. "
        "CRITICAL: 'You never appear on camera — this is a behind-the-scenes role.' "
        "Weekly Sunday payments (huge selling point). "
        "Tone: professional but warm, empowering. Language: English."
    ),
    "ng": (
        "Target: Nigeria. "
        "Emphasize: Earn in USD — $150/week starting (huge vs local salaries). "
        "Weekly Sunday payments via USDT or bank transfer. "
        "Work from anywhere — just need PC + internet. "
        "Paid training $30/shift for 5-7 days. Personal mentor. "
        "Team across 15+ countries — international exposure. "
        "Behind the scenes role — no camera, no content creation. "
        "Tone: energetic, opportunity-focused, emphasize growth. Language: English."
    ),
    "latam": (
        "Target: Latin America (Brazil, Argentina, Colombia, Mexico). "
        "Emphasize: Earn $600-1,600/month in USD working from home. "
        "Weekly payments — every Sunday without fail. "
        "Flexible shifts — choose morning, day, evening, or night. "
        "Paid training with personal mentor. International team. "
        "For CONTENT CREATOR / MODEL role: separate track, different compensation. "
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
