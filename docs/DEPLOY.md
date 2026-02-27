# Деплой HuntMe System

## Бесплатные альтернативы хостинга (для России)

Oracle Cloud НЕ работает из РФ. Вот бесплатные альтернативы:

### Вариант 1: Render.com + Railway (рекомендуется)

**Render.com (бесплатный tier):**
- Telegram Bot: Web Service (free) — поддерживает Docker
- PostgreSQL: Free tier (90 дней, потом $7/мес или мигрировать)
- Минус: сервис засыпает после 15 мин неактивности
- Решение: GitHub Actions пингует каждые 14 мин

**Railway.app:**
- $5 бесплатного кредита на старте
- Хватит на 2-3 недели бота + PostgreSQL
- После — $5/мес (оплата из первых выплат HuntMe)

### Вариант 2: Бесплатные VPS

| Провайдер | Ресурсы | Срок | Ограничения |
|-----------|---------|------|-------------|
| **Hetzner** (через VPN при регистрации) | 1 CPU, 1GB RAM | 1 мес trial | Нужна карта |
| **Google Cloud** | e2-micro VM | Always Free | Нужна карта, 1 инстанс |
| **AWS** | t2.micro | 12 мес Free Tier | Нужна карта |
| **Fly.io** | 3 shared VMs | Free tier | 256MB RAM каждая |
| **Koyeb** | 1 сервис | Free tier | 512MB RAM |

### Вариант 3: Fly.io (лучший бесплатный без карты)

Fly.io даёт 3 бесплатных VM (shared-cpu-1x, 256MB RAM).
Хватит для бота + PostgreSQL.

```bash
# Установка
curl -L https://fly.io/install.sh | sh

# Деплой бота
cd bot
fly launch --name huntme-bot
fly deploy

# PostgreSQL
fly postgres create --name huntme-db
fly postgres attach huntme-db --app huntme-bot
```

### Вариант 4: Локально на домашнем ПК (если есть)

Если есть домашний ПК, который всегда включен:
```bash
docker-compose up -d
```

Для внешнего доступа (n8n webhooks):
- Cloudflare Tunnel (бесплатно): `cloudflared tunnel --url http://localhost:5678`
- ngrok (бесплатно): `ngrok http 5678`

### Вариант 5: n8n Cloud (для n8n отдельно)

n8n.cloud даёт бесплатный trial на 14 дней.
Бота деплоим на Render/Fly, n8n — на n8n.cloud.

---

## Быстрый старт (Render.com)

### 1. PostgreSQL

1. Зайти на render.com → New → PostgreSQL
2. Name: huntme-db
3. Free plan
4. Скопировать Internal Database URL

### 2. Telegram Bot

1. render.com → New → Web Service
2. Connect GitHub repo: DimonProgrammer/HuntMe
3. Root Directory: `bot`
4. Build Command: `pip install -r requirements.txt`
5. Start Command: `python -m bot.main`
6. Environment Variables:
   - `BOT_TOKEN` = токен от @BotFather
   - `ADMIN_CHAT_ID` = твой Telegram ID
   - `CLAUDE_API_KEY` = ключ Anthropic или OpenRouter
   - `DATABASE_URL` = Internal URL из шага 1
   - `REFERRAL_LINK` = твоя реферальная ссылка HuntMe

### 3. n8n (опционально)

Для начала можно работать без n8n — бот сам делает скрининг.
Подключить n8n позже когда появится бюджет ($5-10/мес).

---

## Пошаговый чеклист

1. [ ] Создать бота: написать @BotFather → /newbot → скопировать токен
2. [ ] Узнать свой Telegram ID: написать @userinfobot
3. [ ] Зарегистрироваться на render.com (через GitHub)
4. [ ] Создать PostgreSQL на Render
5. [ ] Задеплоить бота на Render
6. [ ] Проверить: написать боту /help
7. [ ] Получить API key: console.anthropic.com или openrouter.ai
8. [ ] Получить реф-ссылку: huntmecrm.com/request-call/create
9. [ ] Начать постить на бесплатных площадках
