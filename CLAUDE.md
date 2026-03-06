# HuntMe — CLAUDE.md

## Проект

**Apex Talent** — рекрутинг моделей и операторов live-стриминга.

- **Модели:** LatAm (BR → CO → AR) — основной фокус. Онлайн-оффер
- **Операторы:** PH, ID, NG — мужчины (девушек на операторов НЕ берут)

Бот (@apextalent_bot) собирает заявки → AI скрининг → админ approve/reject.
Лендинг (apextalent.pro) собирает лиды → webhook → бот уведомляет админа.
Отдельные сайты под каждую вакансию (НЕ один общий — диссонанс по ролям).

## Правила работы

- После правок файлов → `git push` (Vercel и Render автодеплой). Используй `/ship`
- Название роли: **Live Stream Operator** (не Moderator)
- Approve/Reject кандидатов — ТОЛЬКО ручной (кнопка в admin-чате). AI не авто-аппрувит
- Перед Edit файла → всегда сначала Read
- При новой проблеме → починить + добавить строку в Gotchas ниже
- Не класть в MEMORY.md: TODO-листы, полную документацию, историю изменений
- При обновлении памяти → фиксировать в ОБОИХ файлах: `~/.claude/projects/.../memory/MEMORY.md` (локальный) и `MEMORY.md` в корне репо (GitHub)
- Живой контекст: `gh issue view 1 --repo DimonProgrammer/HuntMe`

## Двуязычность (EN/RU)

**Лендинг**: две версии — `landing/index.html` (EN) и `landing/ru/index.html` (RU).
**Бот**: модуль `bot/messages/` с `en.py` и `ru.py`. Язык определяется из deep link (`land_ru_*`) или TG locale.

**Правило**: любые правки контента вносить сразу на обе версии (EN + RU), учитывая грамотный перевод и региональную специфику. Исключение — если явно сказано, что правка только для одной версии.

- EN-версия — универсальная, без привязки к конкретным странам/платёжным системам
- RU-версия — для СНГ-рынка, social proof с СНГ-именами
- Оплата на обеих версиях: только **$USD** (без GCash, OPay, Wise, USDT и др.)
- Deep link формат: `land_{id}` (EN), `land_ru_{id}` (RU)

## Gotchas (учимся на ошибках)

- `asyncpg` не принимает `sslmode` в URL → `config.py:_fix_db_url()` стрипает
- Gemini API — quota=0 (региональное ограничение). Не работает
- OpenRouter API key — невалидный (401). Не работает
- Единственный рабочий AI: **Groq** (llama-3.3-70b-versatile, free)
- Notion MCP OAuth ≠ Internal Integration Token. Бот использует свой токен через REST API
- Render free tier засыпает → UptimeRobot пингует `/healthz` каждые 5 мин
- Supabase free tier паузит БД → мигрировали на Neon
- HuntMe CRM session token ~30 дней, auto-relogin при 401
- HuntMe CRM за CloudFront — обязательно реалистичный User-Agent
- CRM form — multipart/form-data, НЕ JSON. Слот строго `dd.MM.yyyy HH:mm`
- CRM question_id (49-52) привязаны к office_id=95. При смене офиса могут измениться
- CRM cookie = `__Secure-authjs.session-token` (Auth.js v5, НЕ next-auth)
- CRM create returns 201 (не 200). Telegram поле — без `@`
- CRM поле `number` — полный международный номер БЕЗ стрипа (e.g. `639670997638`, не `9670997638`)
- CRM слоты доступны только на 4 дня вперёд. Новые открываются ровно в 00:00 МСК. `filter_slots_by_window(days=4)`
- CRM status API: PATCH `/api/backend/requests/{id}/status` с `{"status": "i-10"}` (confirmed) / `{"status": "i-60"}` (not confirmed)

## Workflow

### Принципы

- Always use Context7 MCP when needing library/API documentation, code generation, setup or configuration steps — without waiting for explicit request
- Один чат = одна задача. Не смешивать контексты
- Нетривиальная задача → Plan Mode сначала
- Контекст в файлах (knowledge/, CLAUDE.md), НЕ в голове
- Кодинг → /ship. Некодинг → Claude предлагает отметить в TickTick
- Пик 14-18: deep work. Утро/вечер: лиды, контент, настройка
- /status — быстрый взгляд. /plan — планирование. /prep — подготовка

### Поведение Claude (авто)

- Начало сессии без конкретной задачи → проверить TickTick и предложить что делать
- Начало сессии с задачей → работать сразу, не отвлекать
- Задача завершена (любая) → предложить отметить в TickTick
- Пользователь упоминает новую задачу → предложить добавить в TickTick
- Большая задача → предложить разбить на подзадачи (checklist)
- Много переключений контекста в чате → мягко предложить новый чат

### TickTick

- Claude управляет TickTick через MCP, пользователь НЕ открывает TickTick напрямую
- HuntMe project_id: `69a68e303572d1be7bd16fec`
- Приоритеты: 5=High, 3=Medium, 1=Low, 0=None
- Даты ISO 8601, timezone Asia/Yekaterinburg
- Подзадачи через checklist parameter

## База знаний

Главный навигатор: **`knowledge/INDEX.md`** — карта всех файлов, быстрый доступ по задаче.

| Папка | Содержание | Файлов |
|-------|------------|--------|
| `knowledge/models/` | Скрипты, возражения, устройства, фото-гайд, удержание, скрининг | 8 |
| `knowledge/operators/` | Скрипты, возражения, железо, квалификация | 6 |
| `knowledge/general/` | Кампания, быстрый старт, партнёрство, выплаты, CRM-заявки | 5 |
| `knowledge/marketing/` | Навигатор по `research/` и `Скрижаль/` | 1 |

**Иерархия источников:** knowledge/ (структурированная) → docs/ (гайды) → research/ (исследования) → Скрижаль/ (методология)

**Правило:** при правке скриптов/возражений/условий — менять в `knowledge/`, это единый источник правды.

## Архитектура

**Стек:** Python + aiogram 3.x + SQLAlchemy async + aiohttp | Neon PostgreSQL | Vercel | Render

**Ключевые связи (неочевидные из кода):**
- `menu.py` /start → создаёт запись в Notion (`notion_leads.on_start`)
- `operator_flow.py` → синхронизирует каждый шаг FSM в Notion
- `landing/index.html` форма → POST `apex-talent-bot.onrender.com/webhook/landing`
- AI fallback chain: Groq → Gemini → OpenRouter → Anthropic (реально работает только Groq)
- Роутеры в `main.py`: admin → interview_booking → menu → operator_flow (порядок важен!)
- `bot/messages/` — i18n модуль: `en.py` (англ.), `ru.py` (рус.). Все user-facing строки здесь
- `agent_flow.py`, `model_flow.py` — Phase 2, роутеры НЕ подключены
- `interview_booking.py` — CRM auto-booking flow, роутер подключён
- `huntme_crm.py` → авторизация через NextAuth session cookie → fetch слотов + submit заявки

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

**Env vars (Render):** BOT_TOKEN, ADMIN_CHAT_ID, DATABASE_URL, GROQ_API_KEY, NOTION_TOKEN, NOTION_LEADS_DB_ID, LIVE_FEED_CHANNEL_ID, HUNTME_CRM_LOGIN, HUNTME_CRM_PASSWORD, PORT=10000
