# HuntMe — CLAUDE.md

## Проект

**Apex Talent** — международный рекрутинг операторов live-стриминга, агентов и контент-мейкеров.
Регионы: Филиппины · Индонезия · Нигерия · LatAm.
Монетизация: реферальные выплаты HuntMe CRM + платформенные bounty (Chaturbate, Stripchat, LiveJasmin, BongaCams).

Ключевые документы: `STRATEGY.md` (маркетинг), `DEPLOY.md` (деплой), `fb-automation-playbook.jsx` (FB-автоматизация).

## Живой контекст проекта (GitHub Issues)

> Актуальный контекст в issue #1. Обновляй после каждого созвона или принятого решения.

```bash
# Читать:
gh issue view 1 --repo DimonProgrammer/HuntMe

# Обновить:
gh issue edit 1 --repo DimonProgrammer/HuntMe --body "..."

# Активные задачи:
gh issue list --label in-progress --repo DimonProgrammer/HuntMe --state open
```

## Ключевые файлы

- `bot/main.py` — точка входа бота
- `bot/handlers/menu.py` — главное меню (/start, 3 кнопки → operator flow)
- `bot/handlers/operator_flow.py` — 11-шаговый FSM оператора (активен)
- `bot/handlers/admin.py` — approve/reject + reply на вопросы кандидатов
- `bot/services/objection_handler.py` — 15 паттернов возражений (Acknowledge-Reframe-Bridge)
- `bot/services/hardware_checker.py` — валидация CPU/GPU кандидатов
- `bot/services/claude_client.py` — AI скрининг (OpenRouter / Anthropic)
- `bot/services/followup.py` — шаблоны follow-up сообщений
- `bot/handlers/agent_flow.py` — FSM агента (Phase 2, роутер отключён)
- `bot/handlers/model_flow.py` — FSM модели (Phase 2, роутер отключён)
- `landing/index.html` — лендинг
- `landing/kb.html` — база знаний (пароль 8008)
- `STRATEGY.md` — маркетинговая стратегия
- `DEPLOY.md` — инструкция по деплою (Render.com)

## Стек

- Python + aiogram 3.x + SQLAlchemy async (SQLite локально, PostgreSQL на Render)
- OpenRouter (meta-llama/llama-3.1-8b-instruct:free) — AI скрининг кандидатов
- Лендинг: static HTML/JS (Vercel, автодеплой при push)
- Follow-up автоматизация: Phase 2 (APScheduler)

## Текущая фаза: Operator-only (Phase 1)

Активен только operator flow. Agent и Model flows готовы, но роутеры не подключены в main.py.
Кандидат может в любой момент задать вопрос — бот проверяет objection_handler, если не найдено → пересылает админу.
Админ отвечает reply на пересланное сообщение → ответ доставляется кандидату.
