# HuntMe CRM — MCP Server

Позволяет Клоду смотреть слоты и бронировать интервью в HuntMe CRM прямо из чата.

## Инструменты

| Tool | Что делает |
|---|---|
| `check_crm` | Проверяет подключение и авторизацию |
| `get_slots` | Показывает доступные слоты (Manila time) |
| `book_candidate` | Подаёт заявку в CRM |

## Установка

### 1. Зависимости

```bash
cd crm-mcp
pip install -r requirements.txt
```

### 2. Credentials

Добавь в `.env` в корне проекта (уже должны быть):

```
HUNTME_CRM_BASE_URL=https://app.huntme.pro
HUNTME_CRM_LOGIN=твой_логин
HUNTME_CRM_PASSWORD=твой_пароль
```

---

### Claude Code

`.mcp.json` уже лежит в корне репо — заполни `HUNTME_CRM_LOGIN` и `HUNTME_CRM_PASSWORD`.

Либо просто держи `.env` — сервер подтягивает его автоматически.

---

### Claude Desktop

Добавь в `~/Library/Application Support/Claude/claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "huntme-crm": {
      "command": "python3",
      "args": ["/полный/путь/до/HuntMe/crm-mcp/server.py"]
    }
  }
}
```

Перезапусти Claude Desktop.

---

## Примеры использования

**Посмотреть слоты:**
> Show me available interview slots

**Забронировать:**
> Book Mark Joshua G Serrano, born 15.05.1998, phone +639664469038, telegram markjoshua, slot 05.03.2026 18:00, English B2, working currently

**Проверить связь:**
> Check CRM connection
