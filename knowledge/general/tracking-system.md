# Система трекинга трафика — Apex Talent

> Источник: внедрено 7 марта 2026. Сквозной трекинг клик → конверсия.

---

## Как работает (полная цепочка)

```
Реклама (FB/TikTok/Jiji/etc)
  → URL с UTM-параметрами → apextalent.pro
  → JS сохраняет параметры в sessionStorage
  → Форма → POST /webhook/landing (с tracking-данными)
  → Neon PostgreSQL (candidates таблица)
  → Deep link: t.me/apextalent_bot?start=land_{id}
  → Бот подгружает tracking из candidate record
  → FSM несёт tracking через весь флоу
  → Нотифицирует Notion (source/campaign/click_id)
  → При конверсии: постбэк → трекер (если POSTBACK_URL задан)
```

---

## Параметры URL (какие захватываем)

| Параметр | Пример | Что означает |
|----------|--------|--------------|
| `utm_source` | `facebook` | Источник трафика |
| `utm_medium` | `cpc` | Тип трафика |
| `utm_campaign` | `br_models_mar` | Название кампании |
| `utm_content` | `video_gabii_v2` | Креатив/объявление |
| `utm_term` | `modelo online` | Ключевое слово |
| `click_id` | `abc123` | Уникальный ID клика из трекера |
| `sub1`–`sub5` | `br_girl_25` | Доп. параметры (аффилиат/сегмент) |
| `referrer` | `https://fb.com/...` | HTTP-реферер (авто) |

**Пример URL кампании:**
```
https://apextalent.pro/?utm_source=facebook&utm_medium=cpc&utm_campaign=br_models_mar26&utm_content=video_gabii_v2&click_id={clickid}
```
Где `{clickid}` — макрос из рекламного кабинета или трекера.

---

## База данных — таблица candidates

Все tracking-поля хранятся в записи кандидата:

```sql
-- Посмотреть распределение по источникам
SELECT utm_source, utm_campaign, COUNT(*) as leads,
       SUM(CASE WHEN status = 'screened' THEN 1 ELSE 0 END) as qualified,
       SUM(CASE WHEN status = 'interview_invited' THEN 1 ELSE 0 END) as interviews
FROM candidates
WHERE created_at > NOW() - INTERVAL '7 days'
GROUP BY 1, 2 ORDER BY 3 DESC;

-- Стоимость лида по источнику (нужно знать расходы вручную)
SELECT utm_source, utm_medium, utm_campaign,
       COUNT(*) as leads,
       COUNT(CASE WHEN recommendation = 'PASS' THEN 1 END) as qualified,
       COUNT(CASE WHEN status = 'interview_invited' THEN 1 END) as booked
FROM candidates
GROUP BY 1, 2, 3
ORDER BY leads DESC;

-- Найти кандидата по click_id
SELECT * FROM candidates WHERE click_id = 'abc123';
```

---

## Постбэки — конверсионные события

**Env var:** `POSTBACK_URL` на Render (пустой пока нет трекера)

**Формат шаблона:**
```
https://tracker.example.com/postback?clickid={click_id}&status={status}&payout={payout}
```

| Событие | status | Где в коде | Когда |
|---------|--------|-----------|-------|
| Лид | — | main.py webhook | При заполнении формы |
| Квалифицирован | `qualified` | operator_flow.py / model_flow.py | AI дал PASS |
| Интервью забронировано | `interview` | interview_booking.py | CRM submit успешен |

---

## Notion Leads — что видим в дашборде

При /start в боте создаётся/обновляется запись в Notion Leads DB:

| Поле | Откуда |
|------|--------|
| Source | utm_source (маппинг: fb_ph→Facebook, jiji→Jiji и т.д.) |
| Medium | utm_medium |
| Campaign | utm_campaign |
| Click ID | click_id |
| Stage | Текущий шаг воронки (1-11 для операторов) |
| Status | Started → In Progress → Qualified / Rejected |

---

## Аналитика — Metabase (план)

**Статус:** планируется. Self-hosted, бесплатно, на Hetzner CX22 (там же WAHA-бот).

**Установка (Docker):**
```bash
docker run -d -p 3000:3000 \
  -e MB_DB_TYPE=h2 \
  --name metabase \
  metabase/metabase
```
Подключить к Neon PostgreSQL через connection string.

**Ключевые дашборды для Metabase:**
1. **Воронка по неделям** — leads → qualified → interview (по источнику)
2. **Качество по кампании** — conversion rate per campaign
3. **Топ источники** — какой utm_source даёт лучший CPL
4. **Динамика по дням** — тренд новых лидов

**Альтернатива (облако):** metabase.com — free tier, 5 сохранённых запросов. Без Docker.

---

## Яндекс.Метрика (уже есть)

ID: **107023862** (в `landing/index.html`)

Отслеживает:
- Просмотры страниц / сессии
- Кликмапа + вебвизор
- Оформление заявки (submit формы)

**Не видит:** что происходит после редиректа в Telegram (конверсии в боте).

---

## Лендинги (какие есть, все с трекингом)

| Лендинг | URL | deep_link |
|---------|-----|-----------|
| Оператор EN | apextalent.pro | `land_{id}` |
| Оператор RU | apextalent.pro/ru | `land_ru_{id}` |
| Агент EN | apextalent.pro/agent | `agent_{id}` |
| Агент EN v1 | apextalent.pro/agent/v1 | `agent_{id}` |
| Агент PT | apextalent.pro/agent/pt | `agent_{id}` |
| Агент RU | apextalent.pro/agent/ru | `agent_{id}` |

---

## Файлы системы трекинга

| Файл | Роль |
|------|------|
| `landing/*/index.html` | Захват UTM → sessionStorage → webhook |
| `bot/main.py` (landing_webhook) | Приём и сохранение tracking в БД |
| `bot/database/models.py` (Candidate) | 11 tracking-полей в таблице |
| `bot/handlers/menu.py` | Прокидывание tracking из DB → FSM → Notion |
| `bot/services/notion_leads.py` | Запись source/campaign/click_id в Notion |
| `bot/services/postback.py` | Отправка постбэков при конверсии |
| `bot/handlers/operator_flow.py` | Постбэк "qualified" при PASS |
| `bot/handlers/model_flow.py` | Постбэк "qualified" при PASS |
| `bot/handlers/interview_booking.py` | Постбэк "interview" при CRM submit |
| `bot/config.py` | POSTBACK_URL env var |
