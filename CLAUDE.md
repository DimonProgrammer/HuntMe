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
- `bot/handlers/menu.py` — главное меню (/start)
- `bot/handlers/operator_flow.py` — 11-шаговый FSM оператора
- `bot/handlers/agent_flow.py` — 6-шаговый FSM агента
- `bot/handlers/model_flow.py` — 7-шаговый FSM модели
- `bot/handlers/admin.py` — approve/reject callbacks
- `landing/index.html` — лендинг
- `STRATEGY.md` — маркетинговая стратегия
- `DEPLOY.md` — инструкция по деплою (Render.com)

## Стек

- Python + aiogram 3.x + PostgreSQL (SQLAlchemy async)
- Claude API / OpenRouter — AI скрининг кандидатов
- Лендинг: static HTML/JS (Vercel)
- n8n — автоматизация (опционально, `n8n-workflows/`)
