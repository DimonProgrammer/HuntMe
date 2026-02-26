# HuntMe CRM — MCP Server

MCP-сервер для работы с HuntMe CRM прямо из Claude Desktop или Claude Code.

Позволяет смотреть доступные слоты для интервью и бронировать кандидатов одной командой — без ручного входа в CRM.

---

## Что умеет

| Инструмент | Описание |
|---|---|
| `check_crm` | Проверить подключение и авторизацию |
| `get_slots` | Показать ближайшие доступные слоты (время Manila, GMT+8) |
| `book_candidate` | Подать заявку кандидата в CRM и забронировать слот |

---

## Установка

### 1. Клонируй репо

```bash
git clone https://github.com/DimonProgrammer/huntme-crm-mcp
cd huntme-crm-mcp
```

### 2. Установи зависимости

```bash
pip install -r requirements.txt
```

Нужен Python 3.10+.

### 3. Создай `.env`

```bash
cp .env.example .env
```

Заполни credentials:

```env
HUNTME_CRM_BASE_URL=https://app.huntme.pro
HUNTME_CRM_LOGIN=твой_логин
HUNTME_CRM_PASSWORD=твой_пароль
```

---

## Подключение к Claude

### Claude Desktop

Открой конфиг:
- macOS: `~/Library/Application Support/Claude/claude_desktop_config.json`
- Windows: `%APPDATA%\Claude\claude_desktop_config.json`

Добавь секцию `mcpServers`:

```json
{
  "mcpServers": {
    "huntme-crm": {
      "command": "python3",
      "args": ["/полный/путь/до/huntme-crm-mcp/server.py"]
    }
  }
}
```

Перезапусти Claude Desktop. В левом нижнем углу появится иконка 🔧 — сервер подключён.

### Claude Code

Добавь `.mcp.json` в корень своего проекта:

```json
{
  "mcpServers": {
    "huntme-crm": {
      "command": "python3",
      "args": ["/полный/путь/до/huntme-crm-mcp/server.py"]
    }
  }
}
```

---

## Использование

После подключения просто пиши Клоду на естественном языке:

**Посмотреть слоты:**
```
Покажи доступные слоты для интервью
```
или
```
Show me available interview slots
```

**Забронировать кандидата:**
```
Book Mark Joshua G Serrano, born 15.05.1998,
phone +639664469038, telegram markjoshua,
slot 05.03.2026 18:00, English B2 Upper-Intermediate,
currently working
```

**Проверить подключение:**
```
Check CRM connection
```

---

## Параметры book_candidate

| Параметр | Обязательный | Описание | Пример |
|---|---|---|---|
| `name` | ✅ | Полное имя | `Mark Joshua G Serrano` |
| `birth_date` | ✅ | Дата рождения | `15.05.1998` |
| `phone` | ✅ | Телефон с кодом страны | `+639664469038` |
| `telegram` | ✅ | Ник в Telegram (без @) | `markjoshua` |
| `slot` | ✅ | Слот из get_slots | `05.03.2026 18:00` |
| `english_level` | — | Уровень английского | `B2 Upper-Intermediate` |
| `experience` | — | Опыт работы | `Currently working as VA` |
| `additional_notes` | — | Заметки для интервьюера | `Available evenings` |

Слот берётся из вывода `get_slots` в формате `dd.MM.yyyy HH:mm`.

---

## Технические детали

- Авторизация через Auth.js v5 session cookie (`__Secure-authjs.session-token`)
- Токен кешируется на 24 часа, при 401 — автоматический реlogин
- Форма отправляется как `multipart/form-data` (не JSON)
- Воскресенья фильтруются из списка слотов
- Слоты ближе 2 часов от текущего времени не показываются

---

## Требования

- Python 3.10+
- `mcp >= 1.0.0`
- `aiohttp >= 3.9.0`
- Доступ к `app.huntme.pro`
