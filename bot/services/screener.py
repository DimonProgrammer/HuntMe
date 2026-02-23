import json
import logging
from dataclasses import dataclass

from bot.services.claude_client import claude

logger = logging.getLogger(__name__)

SCREENING_SYSTEM_PROMPT = """\
You are an HR screening assistant for a remote chat moderator position.
Evaluate candidates and return ONLY valid JSON — no markdown, no extra text.

Scoring criteria (each 1-10):
1. english_score: Grammar, vocabulary, coherence in their written responses.
2. experience_score: Years/quality of VA/admin/support/online work.
3. availability_score: 6+ hrs/day = 10, 4-5 hrs = 6, <4 hrs = 3.
4. equipment_score: PC + stable internet = 10, phone + ok internet = 5, no equipment = 2.
5. motivation_score: Enthusiasm, specificity, professionalism.

overall_score = weighted average (english 30%, availability 25%, motivation 20%, equipment 15%, experience 10%), scaled to 1-100.

Recommendation:
- overall_score >= 70: "PASS"
- overall_score 50-69: "MAYBE"
- overall_score < 50: "REJECT"

Also generate a suggested_response — a friendly, personalized message to send back to the candidate in English.
For PASS: invite them to the next step.
For MAYBE: ask clarifying questions.
For REJECT: polite decline with encouragement."""

SCREENING_USER_TEMPLATE = """\
Screen this candidate for a Remote Chat Moderator position:

Name: {name}
Experience: {experience}
English Level (self-reported): {english_level}
Availability: {availability}
Expected Rate: {expected_rate}
Additional Message: {message}

Return JSON:
{{"english_score": <int>, "experience_score": <int>, "availability_score": <int>, "equipment_score": <int>, "motivation_score": <int>, "overall_score": <int 1-100>, "recommendation": "PASS"|"MAYBE"|"REJECT", "reasoning": "<brief>", "suggested_response": "<message>"}}"""


@dataclass
class ScreeningResult:
    english_score: int
    experience_score: int
    availability_score: int
    equipment_score: int
    motivation_score: int
    overall_score: int
    recommendation: str  # PASS, MAYBE, REJECT
    reasoning: str
    suggested_response: str


async def screen_candidate(
    name: str,
    experience: str = "N/A",
    english_level: str = "N/A",
    availability: str = "N/A",
    expected_rate: str = "N/A",
    message: str = "N/A",
) -> ScreeningResult:
    prompt = SCREENING_USER_TEMPLATE.format(
        name=name,
        experience=experience,
        english_level=english_level,
        availability=availability,
        expected_rate=expected_rate,
        message=message,
    )

    raw = await claude.complete(
        system=SCREENING_SYSTEM_PROMPT,
        user_message=prompt,
        max_tokens=500,
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
            english_score=0, experience_score=0, availability_score=0,
            equipment_score=0, motivation_score=0, overall_score=0,
            recommendation="MAYBE",
            reasoning="Failed to parse AI response — manual review needed",
            suggested_response="Thank you for applying! Our team will review your application shortly.",
        )

    return ScreeningResult(**data)
