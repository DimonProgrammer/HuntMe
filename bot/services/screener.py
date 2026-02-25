"""AI-powered candidate screening with hard disqualifiers.

Based on official HuntMe screening criteria:
- Hardware compatibility (CPU/GPU/internet)
- Age 18+
- No in-person students
- PC/laptop required
- English B1+ required
"""

import json
import logging
from dataclasses import dataclass

from bot.services.claude_client import claude

logger = logging.getLogger(__name__)

SCREENING_SYSTEM_PROMPT = """\
You are an HR screening assistant for a Live Stream Moderator position at a talent agency.
Evaluate candidates and return ONLY valid JSON — no markdown, no extra text.

IMPORTANT CONTEXT:
- This is a BEHIND THE SCENES role — the moderator never appears on camera
- Job: OBS setup, chat moderation, scheduling for streamers
- Pay: $150/week starting, growth to $200-400+/week
- Schedule: 5/2, 6-8 hours/day, 4 shift options
- Training: 5-7 days paid ($30/shift) with personal mentor
- NEVER mention "HuntMe" — this is the internal company name

HARD DISQUALIFIERS (auto-REJECT if any is true):
- has_pc is false → REJECT
- age < 18 → REJECT
- study_status is "student_inperson" → REJECT
- hardware_compatible is false → REJECT
- english_level is "beginner" or "A1" or "A2" → REJECT

Scoring criteria (each 1-10):
1. english_score: Grammar, vocabulary, coherence in their written responses. B1=6, B2=8, C1+=9
2. hardware_score: Compatible CPU+GPU+internet = 10, partial issues = 5, incompatible = 2
3. availability_score: Ready to start within 1 week = 10, 2 weeks = 6, later = 3
4. motivation_score: Enthusiasm, response quality, engagement during application
5. experience_score: VA/admin/support background = bonus but NOT required

overall_score = weighted average (hardware 30%, english 25%, availability 20%, motivation 15%, experience 10%), scaled to 1-100.

Recommendation:
- overall_score >= 70 AND no hard disqualifiers: "PASS"
- overall_score 50-69: "MAYBE"
- overall_score < 50 OR any hard disqualifier: "REJECT"

For PASS: invite to Zoom interview, be enthusiastic
For MAYBE: ask 1-2 specific clarifying questions
For REJECT: polite, warm decline with encouragement"""

SCREENING_USER_TEMPLATE = """\
Screen this candidate for a Live Stream Moderator position:

Name: {name}
Has PC/Laptop: {has_pc}
Age: {age}
Study/Work Status: {study_status}
English Level: {english_level}
PC Confidence: {pc_confidence}
CPU Model: {cpu_model} (hardware check: {cpu_status})
GPU Model: {gpu_model} (hardware check: {gpu_status})
Hardware Compatible: {hardware_compatible}
Internet Speed: {internet_speed}
Ready to Start: {start_date}
Contact: {contact_info}
Telegram: @{tg_username}

Return JSON:
{{"english_score": <int>, "hardware_score": <int>, "availability_score": <int>, "motivation_score": <int>, "experience_score": <int>, "overall_score": <int 1-100>, "recommendation": "PASS"|"MAYBE"|"REJECT", "reasoning": "<brief>", "suggested_response": "<message to candidate>"}}"""


@dataclass
class ScreeningResult:
    english_score: int
    hardware_score: int
    availability_score: int
    motivation_score: int
    experience_score: int
    overall_score: int
    recommendation: str  # PASS, MAYBE, REJECT
    reasoning: str
    suggested_response: str


async def screen_candidate(
    name: str = "N/A",
    has_pc: bool = None,
    age: int = None,
    study_status: str = "N/A",
    english_level: str = "N/A",
    pc_confidence: str = "N/A",
    cpu_model: str = "N/A",
    gpu_model: str = "N/A",
    cpu_status: str = "N/A",
    gpu_status: str = "N/A",
    hardware_compatible: bool = None,
    internet_speed: str = "N/A",
    start_date: str = "N/A",
    contact_info: str = "N/A",
    tg_username: str = "N/A",
) -> ScreeningResult:
    prompt = SCREENING_USER_TEMPLATE.format(
        name=name,
        has_pc=has_pc if has_pc is not None else "N/A",
        age=age if age is not None else "N/A",
        study_status=study_status,
        english_level=english_level,
        pc_confidence=pc_confidence,
        cpu_model=cpu_model,
        cpu_status=cpu_status,
        gpu_model=gpu_model,
        gpu_status=gpu_status,
        hardware_compatible=hardware_compatible if hardware_compatible is not None else "N/A",
        internet_speed=internet_speed,
        start_date=start_date,
        contact_info=contact_info,
        tg_username=tg_username,
    )

    raw = await claude.complete(
        system=SCREENING_SYSTEM_PROMPT,
        user_message=prompt,
        max_tokens=600,
    )

    # Strip markdown fences if Claude wraps the JSON
    cleaned = raw.strip()
    if cleaned.startswith("```"):
        cleaned = cleaned.split("\n", 1)[1]
    if cleaned.endswith("```"):
        cleaned = cleaned.rsplit("```", 1)[0]
    cleaned = cleaned.strip()

    try:
        data = json.loads(cleaned)
    except json.JSONDecodeError:
        logger.error("Failed to parse screening response: %s", raw)
        return ScreeningResult(
            english_score=0, hardware_score=0, availability_score=0,
            motivation_score=0, experience_score=0, overall_score=0,
            recommendation="MAYBE",
            reasoning="Failed to parse AI response — manual review needed",
            suggested_response="Thank you for applying! Our team will review your application shortly.",
        )

    return ScreeningResult(**data)
