"""Objection handling based on official HuntMe Objection Handling Guide.

15 common objections with Acknowledge -> Reframe -> Bridge framework.
Rule of One: never push more than once on the same objection.
Bilingual: English + Russian keyword sets, responses via bot.messages.
"""

from typing import Optional

from bot.messages import msg

# Objection key → attribute name in en.py / ru.py
_OBJ_ATTR = {
    "what_is_moderation": "OBJ_WHAT_IS_MODERATION",
    "adult_content": "OBJ_ADULT_CONTENT",
    "scam": "OBJ_SCAM",
    "what_company": "OBJ_WHAT_COMPANY",
    "pay_too_low": "OBJ_PAY_TOO_LOW",
    "need_to_think": "OBJ_NEED_TO_THINK",
    "already_have_job": "OBJ_ALREADY_HAVE_JOB",
    "no_obs_experience": "OBJ_NO_EXPERIENCE",
    "schedule_issues": "OBJ_SCHEDULE",
    "not_interested": "OBJ_NOT_INTERESTED",
    "privacy_concern": "OBJ_PRIVACY",
    "student": "OBJ_STUDENT",
    "office_question": "OBJ_OFFICE",
    "payment_trust": "OBJ_PAYMENT_TRUST",
    "passport_question": "OBJ_PASSPORT",
}

# English keywords
_KEYWORDS_EN = {
    "what_is_moderation": ["what is", "what do", "what does", "moderator do", "what exactly", "explain the job", "what kind of work"],
    "adult_content": ["adult", "nsfw", "webcam", "only fans", "onlyfans", "sexual", "nude", "explicit", "porn", "xxx", "18+"],
    "scam": ["scam", "legit", "legitimate", "real", "fake", "fraud", "trust", "suspicious", "is this real", "too good"],
    "what_company": ["what company", "company name", "who are you", "which company", "name of company", "website"],
    "pay_too_low": ["too low", "not enough", "more money", "higher pay", "low salary", "only 150", "150 is low", "pay more"],
    "need_to_think": ["think about", "need to think", "let me think", "consider", "not sure yet", "decide later", "get back to you"],
    "already_have_job": ["already work", "have a job", "employed", "full time job", "day job", "current job"],
    "no_obs_experience": ["obs", "never used", "don't know obs", "no experience with", "streaming software", "technical"],
    "schedule_issues": ["night shift", "schedule", "hours don't work", "can't work nights", "only morning", "only evening", "timezone"],
    "not_interested": ["not interested", "no thanks", "no thank you", "pass", "don't want", "not for me"],
    "privacy_concern": ["how did you get", "my number", "my contact", "privacy", "where did you find", "data"],
    "student": ["student", "university", "college", "studying", "school", "classes"],
    "office_question": ["office", "in person", "come to office", "location", "where is the office", "on-site"],
    "payment_trust": ["how do i know", "will you pay", "guarantee", "proof of payment", "payment proof", "really pay", "when get paid"],
    "passport_question": ["passport", "need id", "show id", "my id", "send id", "identification", "document", "verify identity", "verification", "personal document"],
}

# Russian keywords
_KEYWORDS_RU = {
    "what_is_moderation": ["что за работа", "что делает", "что нужно делать", "в чём суть", "что такое", "обязанности", "что за вакансия"],
    "adult_content": ["вебкам", "для взрослых", "порно", "интим", "эротика", "онлифанс", "18+", "nsfw"],
    "scam": ["обман", "развод", "мошенники", "кидалово", "лохотрон", "это реально", "не верю", "слишком хорошо", "правда"],
    "what_company": ["что за компания", "название компании", "кто вы", "какая компания", "сайт компании"],
    "pay_too_low": ["мало платят", "маленькая зарплата", "больше денег", "мало", "копейки"],
    "need_to_think": ["подумаю", "надо подумать", "не уверен", "позже", "перезвоню", "решу потом"],
    "already_have_job": ["уже работаю", "есть работа", "занят", "полный день"],
    "no_obs_experience": ["obs", "не умею", "нет опыта", "не знаю как", "стриминг"],
    "schedule_issues": ["ночная смена", "график", "не подходит время", "часовой пояс", "только утро", "только вечер"],
    "not_interested": ["не интересно", "нет спасибо", "не хочу", "не надо", "отстаньте"],
    "privacy_concern": ["откуда номер", "мои данные", "конфиденциальность", "откуда контакт", "персональные данные"],
    "student": ["студент", "учусь", "университет", "институт", "колледж", "занятия"],
    "office_question": ["офис", "приходить", "локация", "где находится", "на месте"],
    "payment_trust": ["как я узнаю", "вы заплатите", "гарантия", "доказательства оплаты", "когда платят"],
    "passport_question": ["паспорт", "документы", "удостоверение", "верификация", "подтверждение личности"],
}


def detect_objection(text: str, lang: str = "en") -> Optional[str]:
    """Detect objection type from candidate's free-text message.

    Checks both English and Russian keyword sets (Russian first if lang=ru).
    Returns objection key or None if no objection detected.
    """
    text_lower = text.lower()

    # Check primary language first, then fallback
    keyword_sets = [_KEYWORDS_RU, _KEYWORDS_EN] if lang == "ru" else [_KEYWORDS_EN, _KEYWORDS_RU]

    best_match: Optional[str] = None
    best_score = 0

    for kw_dict in keyword_sets:
        for obj_key, keywords in kw_dict.items():
            score = 0
            for keyword in keywords:
                if keyword in text_lower:
                    score += len(keyword)
            if score > best_score:
                best_score = score
                best_match = obj_key

    return best_match if best_score > 0 else None


def get_response(objection_type: str, lang: str = "en") -> Optional[str]:
    """Get localized response for an objection type."""
    attr = _OBJ_ATTR.get(objection_type)
    if not attr:
        return None
    m = msg(lang)
    return getattr(m, attr, None)
