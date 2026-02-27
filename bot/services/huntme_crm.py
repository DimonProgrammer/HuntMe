"""HuntMe CRM API client — auth, fetch slots, submit applications, AI form answers.

Uses Auth.js v5 session cookie (__Secure-authjs.session-token) for auth.
All methods are async, follow the same error-handling pattern as notion_leads.py.
"""

import json
import logging
import re
from datetime import datetime, timedelta, timezone
from typing import Optional

import aiohttp

from bot.config import config

logger = logging.getLogger(__name__)

# Manila timezone (UTC+8) — CRM slots are in this timezone
_MANILA_TZ = timezone(timedelta(hours=8))

_USER_AGENT = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36"
)

# Auth.js v5 cookie name (not next-auth.session-token!)
_SESSION_COOKIE = "__Secure-authjs.session-token"

# Session state (module-level singleton)
_session_token: Optional[str] = None
_token_obtained_at: Optional[datetime] = None

# CRM form question IDs for office_id=95 (ENG+OTHER)
_QUESTION_IDS = {"company_name": "49", "english": "50", "experience": "51", "additional": "52"}


def _base_url() -> str:
    return config.HUNTME_CRM_BASE_URL.rstrip("/")


def _base_headers() -> dict:
    return {"User-Agent": _USER_AGENT, "Accept": "application/json"}


async def _login() -> Optional[str]:
    """Authenticate with HuntMe CRM via Auth.js v5.

    Returns session token string or None.
    """
    if not config.HUNTME_CRM_LOGIN or not config.HUNTME_CRM_PASSWORD:
        logger.debug("HuntMe CRM credentials not configured — skipping")
        return None

    base = _base_url()
    try:
        # Use CookieJar so cookies flow between requests in same session
        jar = aiohttp.CookieJar()
        async with aiohttp.ClientSession(
            headers=_base_headers(), cookie_jar=jar
        ) as session:
            # Step 1: get CSRF token (also sets csrf cookie needed for step 2)
            async with session.get(
                f"{base}/api/auth/csrf",
                timeout=aiohttp.ClientTimeout(total=15),
            ) as resp:
                if resp.status != 200:
                    logger.warning("CRM CSRF fetch failed: %s", resp.status)
                    return None
                csrf_data = await resp.json()
                csrf_token = csrf_data.get("csrfToken")
                if not csrf_token:
                    logger.warning("CRM CSRF token missing from response")
                    return None

            # Step 2: login with credentials
            async with session.post(
                f"{base}/api/auth/callback/credentials",
                data={
                    "csrfToken": csrf_token,
                    "login": config.HUNTME_CRM_LOGIN,
                    "password": config.HUNTME_CRM_PASSWORD,
                    "redirect": "false",
                    "callbackUrl": "/dashboard",
                    "json": "true",
                },
                timeout=aiohttp.ClientTimeout(total=15),
                allow_redirects=False,
            ) as resp:
                # Extract session token from Set-Cookie headers
                token = None
                for header_val in resp.headers.getall("Set-Cookie", []):
                    match = re.search(
                        r"__Secure-authjs\.session-token=([^;]+)", header_val
                    )
                    if match:
                        token = match.group(1)
                        break

                # Fallback: check CookieJar
                if not token:
                    for cookie in jar:
                        if cookie.key == _SESSION_COOKIE:
                            token = cookie.value
                            break

                if token:
                    logger.info("HuntMe CRM login successful")
                    return token
                else:
                    logger.warning(
                        "CRM login: no session token in response (status=%s)",
                        resp.status,
                    )
                    return None
    except Exception:
        logger.exception("HuntMe CRM login failed")
        return None


async def _ensure_token() -> Optional[str]:
    """Return cached token or login. Re-login if token is older than 24h."""
    global _session_token, _token_obtained_at

    if _session_token and _token_obtained_at:
        age = datetime.now(timezone.utc) - _token_obtained_at
        if age < timedelta(hours=24):
            return _session_token

    token = await _login()
    if token:
        _session_token = token
        _token_obtained_at = datetime.now(timezone.utc)
    return token


def _auth_cookies() -> dict:
    """Build cookie dict for authenticated requests."""
    if _session_token:
        return {_SESSION_COOKIE: _session_token}
    return {}


async def _request(
    method: str, path: str, retried: bool = False, **kwargs
) -> Optional[dict]:
    """Make authenticated CRM request. Auto-relogin on 401."""
    global _session_token, _token_obtained_at

    token = await _ensure_token()
    if not token:
        return None

    base = _base_url()
    url = f"{base}{path}"
    try:
        async with aiohttp.ClientSession(
            headers=_base_headers(), cookies=_auth_cookies()
        ) as session:
            async with session.request(
                method,
                url,
                timeout=aiohttp.ClientTimeout(total=20),
                **kwargs,
            ) as resp:
                if resp.status in (401, 403) and not retried:
                    logger.info("CRM %s — re-logging in", resp.status)
                    _session_token = None
                    _token_obtained_at = None
                    return await _request(method, path, retried=True, **kwargs)

                if resp.status not in (200, 201):
                    text = await resp.text()
                    logger.warning(
                        "CRM %s %s → %s: %s",
                        method, path, resp.status, text[:300],
                    )
                    return None

                return await resp.json()
    except Exception:
        logger.exception("CRM request failed: %s %s", method, path)
        return None


# ═══ PUBLIC API ═══


async def get_available_slots(office_id: int = 95) -> Optional[dict]:
    """Fetch available interview slots. Filters out Sundays.

    Returns: {"28.02.2026": ["18:00", "19:00"], ...} or None on error.
    """
    data = await _request(
        "GET",
        "/api/backend/interview-appointments/available-dates",
        params={"office_id": office_id, "funnel_key": "operators"},
    )
    if not data:
        return None

    slots = data.get("data")
    if not slots:
        return None

    # Filter out Sundays
    filtered = {}
    for date_str, times in slots.items():
        try:
            dt = datetime.strptime(date_str, "%d.%m.%Y")
            if dt.weekday() == 6:  # Sunday
                continue
            filtered[date_str] = times
        except ValueError:
            continue

    return filtered if filtered else None


def pick_nearest_slots(
    slots: dict, count: int = 5, min_hours: int = 2
) -> list:
    """Pick up to `count` nearest available slots from the dict.

    Returns list of "dd.MM.yyyy HH:mm" strings, sorted chronologically.
    Skips slots closer than min_hours from now (Manila time).
    """
    now_manila = datetime.now(_MANILA_TZ)
    cutoff = now_manila + timedelta(hours=min_hours)

    all_slots = []
    for date_str, times in slots.items():
        for time_str in times:
            try:
                dt = datetime.strptime(
                    "%s %s" % (date_str, time_str), "%d.%m.%Y %H:%M"
                )
                dt = dt.replace(tzinfo=_MANILA_TZ)
                if dt > cutoff:
                    all_slots.append(dt)
            except ValueError:
                continue

    all_slots.sort()
    return [dt.strftime("%d.%m.%Y %H:%M") for dt in all_slots[:count]]


def _guess_phone_country(phone_digits: str) -> str:
    """Guess phone country code from phone number prefix."""
    if phone_digits.startswith("63"):
        return "ph"
    if phone_digits.startswith("62"):
        return "id"
    if phone_digits.startswith("234"):
        return "ng"
    if phone_digits.startswith("7"):
        return "ru"
    if phone_digits.startswith("1"):
        return "us"
    return "ph"  # default for target regions


def parse_phone(raw: str) -> tuple:
    """Extract digits from phone string and guess country.

    Returns: (digits_only, country_code)
    """
    digits = re.sub(r"\D", "", raw)
    country = _guess_phone_country(digits)
    return digits, country


def _build_form_data(
    name: str,
    birth_date: str,
    phone: str,
    phone_country: str,
    telegram: str,
    slot: str,
    crm_answers: dict,
    office_id: int = 95,
) -> aiohttp.FormData:
    """Build multipart form data for CRM application."""
    form_data = aiohttp.FormData()
    form_data.add_field("category", "0")  # Solo
    form_data.add_field("office_id", str(office_id))
    form_data.add_field("interview_appointment_date", slot)
    form_data.add_field("name", name)
    form_data.add_field("birth_date", birth_date)
    form_data.add_field("number", phone)
    form_data.add_field("phone_country", phone_country)
    form_data.add_field("telegram", telegram)
    form_data.add_field(
        "questions_and_answers.0.question_id", _QUESTION_IDS["company_name"]
    )
    form_data.add_field(
        "questions_and_answers.0.answer_text",
        crm_answers.get("company_name", "Apex Talent"),
    )
    form_data.add_field(
        "questions_and_answers.1.question_id", _QUESTION_IDS["english"]
    )
    form_data.add_field(
        "questions_and_answers.1.answer_text",
        crm_answers.get("english_level", "Not specified"),
    )
    form_data.add_field(
        "questions_and_answers.2.question_id", _QUESTION_IDS["experience"]
    )
    form_data.add_field(
        "questions_and_answers.2.answer_text",
        crm_answers.get("experience", "Not specified"),
    )
    form_data.add_field(
        "questions_and_answers.3.question_id", _QUESTION_IDS["additional"]
    )
    form_data.add_field(
        "questions_and_answers.3.answer_text",
        crm_answers.get("additional_notes", "")[:500],
    )
    return form_data


async def submit_application(
    name: str,
    birth_date: str,
    phone: str,
    phone_country: str,
    telegram: str,
    slot: str,
    crm_answers: dict,
    office_id: int = 95,
) -> tuple:
    """Submit candidate application to HuntMe CRM.

    Args:
        crm_answers: dict from generate_crm_answers() with keys:
            company_name, english_level, experience, additional_notes

    Returns: (success: bool, error_message: Optional[str])
    """
    form_data = _build_form_data(
        name, birth_date, phone, phone_country, telegram, slot,
        crm_answers, office_id,
    )

    token = await _ensure_token()
    if not token:
        return False, "CRM authentication failed"

    base = _base_url()
    url = "%s/api/backend/requests/create/operator" % base
    try:
        async with aiohttp.ClientSession(
            headers=_base_headers(), cookies=_auth_cookies()
        ) as session:
            async with session.post(
                url,
                data=form_data,
                timeout=aiohttp.ClientTimeout(total=20),
            ) as resp:
                if resp.status in (200, 201):
                    result = await resp.json()
                    logger.info("CRM application submitted: %s", result)
                    return True, None
                elif resp.status in (401, 403):
                    # Re-login and retry once
                    global _session_token, _token_obtained_at
                    _session_token = None
                    _token_obtained_at = None
                    new_token = await _ensure_token()
                    if not new_token:
                        return False, "CRM re-auth failed"
                    # Rebuild form data (aiohttp FormData is consumed)
                    form_data2 = _build_form_data(
                        name, birth_date, phone, phone_country,
                        telegram, slot, crm_answers, office_id,
                    )
                    async with aiohttp.ClientSession(
                        headers=_base_headers(), cookies=_auth_cookies()
                    ) as session2:
                        async with session2.post(
                            url,
                            data=form_data2,
                            timeout=aiohttp.ClientTimeout(total=20),
                        ) as resp2:
                            if resp2.status == 200:
                                result = await resp2.json()
                                logger.info(
                                    "CRM application submitted (retry): %s",
                                    result,
                                )
                                return True, None
                            text = await resp2.text()
                            logger.warning(
                                "CRM submit retry failed: %s %s",
                                resp2.status, text[:300],
                            )
                            return False, "CRM error %s" % resp2.status
                else:
                    text = await resp.text()
                    logger.warning(
                        "CRM submit failed: %s %s", resp.status, text[:300]
                    )
                    return (
                        False,
                        "CRM error %s: %s" % (resp.status, text[:200]),
                    )
    except Exception:
        logger.exception("CRM submit exception")
        return False, "CRM request failed"


# ═══ AI-GENERATED CRM ANSWERS ═══

_CRM_ANSWERS_SYSTEM = """\
You generate answers for a recruitment CRM application form.
You receive candidate data and must produce answers for 4 specific questions.
Answer in English, concise and professional. Return ONLY valid JSON, no markdown.

Context:
- Company name presented to candidates: "Apex Talent"
- Role: Live Stream Operator (behind the scenes — OBS, chat moderation, scheduling)
- This is NOT a modeling/on-camera role

Questions to answer:
1. company_name: Which company name was presented to the candidate?
   → Always "Apex Talent"

2. english_level: What is the candidate's English proficiency level?
   → Translate the bot's level to a CRM-friendly description.
   Map: Beginner→A1-A2, B1→Intermediate, B2→Upper-Intermediate, C1→Advanced, Native→Fluent/Native
   Add brief note if relevant (e.g. "writes clearly", "good grammar in responses")

3. experience: Does the candidate have any relevant prior experience?
   → Summarize from their experience answer + study/work status.
   If no experience, write "No prior experience in streaming/moderation. [study/work status]."
   If yes, highlight relevant parts. Keep it under 200 chars.

4. additional_notes: Any additional notes for the interview
   → Structured brief: availability, hardware status, key strengths, any flags.
   Format: "Available: [start_date]. HW: [compatible/issues]. [strengths]. [flags if any]"
   Keep it under 300 chars."""

_CRM_ANSWERS_USER = """\
Generate CRM form answers for this candidate:

Name: {name}
English Level: {english_level}
Study/Work: {study_status}
Experience (candidate's answer): {experience}
PC Confidence: {pc_confidence}
Hardware Compatible: {hardware_compatible}
CPU: {cpu_model}
GPU: {gpu_model}
Internet: {internet_speed}
Ready to Start: {start_date}
AI Score: {score}/100
AI Recommendation: {recommendation}
AI Reasoning: {reasoning}

Return JSON:
{{"company_name": "...", "english_level": "...", "experience": "...", "additional_notes": "..."}}"""


async def generate_crm_answers(
    name: str,
    english_level: str,
    study_status: str,
    experience: str,
    pc_confidence: str,
    hardware_compatible: str,
    cpu_model: str,
    gpu_model: str,
    internet_speed: str,
    start_date: str,
    score: int,
    recommendation: str,
    reasoning: str,
) -> dict:
    """Use AI to generate professional CRM form answers from candidate data.

    Returns dict with keys: company_name, english_level, experience, additional_notes.
    Falls back to simple templates if AI is unavailable.
    """
    from bot.services.claude_client import claude

    prompt = _CRM_ANSWERS_USER.format(
        name=name,
        english_level=english_level or "Not specified",
        study_status=study_status or "Not specified",
        experience=experience or "No answer provided",
        pc_confidence=pc_confidence or "Not specified",
        hardware_compatible=hardware_compatible or "Not checked",
        cpu_model=cpu_model or "Not specified",
        gpu_model=gpu_model or "Not specified",
        internet_speed=internet_speed or "Not specified",
        start_date=start_date or "Not specified",
        score=score or 0,
        recommendation=recommendation or "MAYBE",
        reasoning=reasoning or "No AI screening data",
    )

    try:
        raw = await claude.complete(
            system=_CRM_ANSWERS_SYSTEM,
            user_message=prompt,
            max_tokens=400,
        )
        # Strip markdown fences
        cleaned = raw.strip()
        if cleaned.startswith("```"):
            cleaned = cleaned.split("\n", 1)[1]
        if cleaned.endswith("```"):
            cleaned = cleaned.rsplit("```", 1)[0]
        cleaned = cleaned.strip()

        data = json.loads(cleaned)
        logger.info("AI generated CRM answers for %s", name)
        return data
    except Exception:
        logger.warning("AI CRM answer generation failed, using fallback", exc_info=True)

    # Fallback: simple template answers
    eng_map = {
        "Beginner": "A1-A2 Basic",
        "B1": "B1 Intermediate",
        "B2": "B2 Upper-Intermediate",
        "C1": "C1 Advanced",
        "Native": "Native/Fluent",
    }
    return {
        "company_name": "Apex Talent",
        "english_level": eng_map.get(english_level, english_level or "Not specified"),
        "experience": experience[:200] if experience else "No prior experience specified",
        "additional_notes": "Available: %s. Score: %s/100." % (
            start_date or "N/A", score or "N/A"
        ),
    }


async def check_connection() -> tuple:
    """Check CRM connectivity: login + fetch slots."""
    if not config.HUNTME_CRM_LOGIN:
        return False, "HUNTME_CRM_LOGIN not configured"

    token = await _login()
    if not token:
        return False, "Login failed"

    # Cache the token for subsequent calls
    global _session_token, _token_obtained_at
    _session_token = token
    _token_obtained_at = datetime.now(timezone.utc)

    slots = await get_available_slots()
    if slots is None:
        return False, "Login OK but slots fetch failed"

    total_slots = sum(len(times) for times in slots.values())
    return True, "Connected. %d days, %d slots available" % (
        len(slots),
        total_slots,
    )
