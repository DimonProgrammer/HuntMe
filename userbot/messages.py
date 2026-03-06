"""Message templates for personal Telegram account outreach.

All messages are sent from the manager's personal account,
so they're warmer and more personal than the bot's messages.
"""

# ── Interview follow-up (day after booking confirmed) ────────────────────────

INTERVIEW_BOOKED_EN = (
    "Hi {name}! 👋\n\n"
    "Just wanted to personally confirm your interview is all set for "
    "**{time} Manila time** (GMT+8) tomorrow.\n\n"
    "A few things to have ready:\n"
    "• Your PC turned on and connected\n"
    "• Stable internet (no mobile data)\n"
    "• Quiet place to chat\n\n"
    "Any questions before then? Feel free to ask here 😊"
)

INTERVIEW_BOOKED_RU = (
    "Привет, {name}! 👋\n\n"
    "Хочу лично подтвердить — всё готово, встреча назначена на "
    "**{time} (время Манилы, GMT+8)**.\n\n"
    "Что подготовить:\n"
    "• ПК включён, интернет через кабель или Wi-Fi (не мобильный)\n"
    "• Тихое место\n"
    "• Минут 30 свободного времени\n\n"
    "Если есть вопросы — пиши сюда, отвечу 😊"
)

# ── Interview no-show follow-up ───────────────────────────────────────────────

INTERVIEW_NOSHOW_EN = (
    "Hi {name}, we missed you at the interview today 😔\n\n"
    "No worries — things happen. Would you like to reschedule?\n"
    "Just reply here and I'll find a new slot for you."
)

INTERVIEW_NOSHOW_RU = (
    "Привет, {name}! Сегодня не дождались тебя на встрече 😔\n\n"
    "Ничего страшного, бывает. Хочешь перенести?\n"
    "Напиши сюда — подберём другое время."
)

# ── Agent warm-up: after bot signup ──────────────────────────────────────────

AGENT_WELCOME_EN = (
    "Hey {name}! 👋 I'm Dima, your contact at Apex Talent.\n\n"
    "Saw you signed up as an agent — great choice! I'll be your direct line "
    "whenever you have questions about recruiting or your referrals.\n\n"
    "Once you're ready to start, let me know and I'll walk you through the first steps."
)

AGENT_WELCOME_RU = (
    "Привет, {name}! 👋 Я Дима, твой куратор в Apex Talent.\n\n"
    "Вижу, ты зарегистрировался как агент — отличное решение! "
    "Я буду твоим прямым контактом по всем вопросам: рефералы, выплаты, что угодно.\n\n"
    "Как будешь готов стартовать — напиши, пройдём первые шаги вместе."
)

# ── Agent 3-day re-engagement (no referrals yet) ─────────────────────────────

AGENT_REENGAGEMENT_EN = (
    "Hi {name}! Just checking in 👋\n\n"
    "It's been a few days since you joined as an agent. "
    "Have you had a chance to share the link with anyone yet?\n\n"
    "If you're not sure how to start or what to say — happy to help with that."
)

AGENT_REENGAGEMENT_RU = (
    "Привет, {name}! Проверяю как дела 👋\n\n"
    "Уже несколько дней как ты в команде агентов. "
    "Успел поделиться ссылкой с кем-нибудь?\n\n"
    "Если не знаешь с чего начать или что говорить — напиши, помогу."
)
