# HuntMe — CLAUDE.md

## Проект

**Apex Talent** — рекрутинг операторов live-стриминга (PH, ID, NG).
Бот (@apextalent_bot) собирает заявки → AI скрининг → админ approve/reject.
Лендинг (apextalent.pro) собирает лиды → webhook → бот уведомляет админа.

## Правила работы

- После правок файлов → `git push` (Vercel и Render автодеплой). Используй `/ship`
- Название роли: **Live Stream Operator** (не Moderator)
- Approve/Reject кандидатов — ТОЛЬКО ручной (кнопка в admin-чате). AI не авто-аппрувит
- Перед Edit файла → всегда сначала Read
- При новой проблеме → починить + добавить строку в Gotchas ниже
- Не класть в MEMORY.md: TODO-листы, полную документацию, историю изменений
- Живой контекст: `gh issue view 1 --repo DimonProgrammer/HuntMe`

## Gotchas (учимся на ошибках)

- `asyncpg` не принимает `sslmode` в URL → `config.py:_fix_db_url()` стрипает
- Gemini API — quota=0 (региональное ограничение). Не работает
- OpenRouter API key — невалидный (401). Не работает
- Единственный рабочий AI: **Groq** (llama-3.3-70b-versatile, free)
- Notion MCP OAuth ≠ Internal Integration Token. Бот использует свой токен через REST API
- Render free tier засыпает → UptimeRobot пингует `/healthz` каждые 5 мин
- Supabase free tier паузит БД → мигрировали на Neon

## Архитектура

**Стек:** Python + aiogram 3.x + SQLAlchemy async + aiohttp | Neon PostgreSQL | Vercel | Render

**Ключевые связи (неочевидные из кода):**
- `menu.py` /start → создаёт запись в Notion (`notion_leads.on_start`)
- `operator_flow.py` → синхронизирует каждый шаг FSM в Notion
- `landing/index.html` форма → POST `apex-talent-bot.onrender.com/webhook/landing`
- AI fallback chain: Groq → Gemini → OpenRouter → Anthropic (реально работает только Groq)
- Роутеры в `main.py`: admin → menu → operator_flow (порядок важен!)
- `agent_flow.py`, `model_flow.py` — Phase 2, роутеры НЕ подключены

**Инфраструктура:**

| Что | Где | Детали |
|---|---|---|
| Бот | Render | apex-talent-bot.onrender.com |
| Лендинг | Vercel | apextalent.pro |
| БД | Neon PostgreSQL | Singapore, pooler endpoint |
| Notion Leads | Notion DB | `237a3a0a251941b3973c74212d6a6ee8` |
| Notion Platforms | Notion DB | `51ad3c249dd240688c24792552cb35c8` |
| Email | Zoho Mail | hello@apextalent.pro |
| Аналитика | Яндекс.Метрика | 107023862 |

**Env vars (Render):** BOT_TOKEN, ADMIN_CHAT_ID, DATABASE_URL, GROQ_API_KEY, NOTION_TOKEN, NOTION_LEADS_DB_ID, LIVE_FEED_CHANNEL_ID, PORT=10000
