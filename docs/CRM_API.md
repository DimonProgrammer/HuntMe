# HuntMe CRM — API Reference

Source: Chrome extension analysis of huntmecrm.com (March 2026).

## Authentication

Auth.js v5 session cookie:
1. `GET /api/auth/csrf` → `{csrfToken}`
2. `POST /api/auth/callback/credentials` → Set-Cookie: `__Secure-authjs.session-token`
3. Token ~30 days, auto-relogin on 401

## Endpoints

### Create Operator
```
POST /api/backend/requests/create/operator
Content-Type: multipart/form-data
```

| Field | Type | Required | Notes |
|---|---|---|---|
| `category` | radio | no | `"0"` Solo, `"1"` Team (default) |
| `office_id` | select | **yes** | 73, 95, 104 |
| `interview_appointment_date` | text | **yes** | `dd.MM.yyyy HH:mm` Manila TZ |
| `name` | text | **yes** | Full name |
| `birth_date` | text | **yes** | `dd.MM.yyyy` |
| `number` | tel | no | LOCAL digits only (no country code) |
| `phone_country` | hidden | no | `"ph"`, `"id"`, `"ng"`, `"ru"` |
| `telegram` | text | no | Without `@` |
| `number_checkbox1` | checkbox | no | Phone is correct |
| `number_checkbox2` | checkbox | no | Knows job requirements |
| `number_checkbox3` | checkbox | no | Will confirm status |
| `questions_and_answers.N.question_id` | hidden | no | Q IDs for office |
| `questions_and_answers.N.answer_text` | textarea | **yes** | Answer text |

Returns: **201** on success.

### Create Agent
```
POST /api/backend/requests/create/agent
Content-Type: multipart/form-data
```

| Field | Type | Notes |
|---|---|---|
| `category` | radio | `"0"` Solo, `"1"` Team |
| `name` | text | Full name |
| `birth_date` | text | `dd.MM.yyyy` |
| `number` | tel | LOCAL digits only |
| `phone_country` | hidden | Country code |
| `telegram` | text | Without `@` |

No office_id, no checkboxes, no questions.

### List Applications
```
GET /api/backend/requests?category={cat}&search={name}&page=1
```
Categories: `operators`, `agents`, `models`

Response:
```json
{
  "data": [{"id": 123, "name": "...", "status": {"label": "...", "value": 0},
            "telegram": {"nickname": "...", "url": "..."},
            "number": {"id": 123, "number": "..."}, ...}],
  "meta": {"last_page": 1},
  "count": 10
}
```

### Get Application Card
```
GET /api/backend/requests/{id}
```
Returns full card with `birth_date`, `questions_and_answers`, `office_id`, etc.

`questions_and_answers[].text_answer` is JSON: `{"data": "actual answer"}`

### Available Slots
```
GET /api/backend/interview-appointments/available-dates?office_id={id}&funnel_key=operators
```

## Office IDs

| office_id | Name | Company |
|---|---|---|
| 73 | Online 2 - RU [1] | Online 2 (id=67) |
| 95 | Online 3 - ENG+OTHER [Time Manila] | Online 3 (id=68) |
| 104 | Online 2 - RU [2] | Online 2 (id=67) |

## Question IDs (office_id=95)

| Index | question_id | Question |
|---|---|---|
| 0 | 49 | Company name presented to candidate |
| 1 | 50 | English proficiency level |
| 2 | 51 | Relevant prior experience |
| 3 | 52 | Additional notes for interview |

## Statuses

| id | label |
|---|---|
| -10 | Отказ в назначении |
| 0 | Назначено |
| 10 | Подтвержден(-а) |
| 20 | Отказ со стороны кандидата |
| 30 | Отказ со стороны партнёра |
| 40 | Перенос |
| 50 | Регистрация |
| 60 | Не подтвержден(-а) |
| 70 | Слив |
| 120 | Успешно |
| 130 | Не успешно |
| 140 | Под вопросом |
| 150 | Запрос |
| 160 | Принят(-а) |

## Companies

| company_id | name |
|---|---|
| 67 | Online 2 |
| 68 | Online 3 |
| 72 | Online 4 |
| 81 | Online 5 |
| 84 | Online 6 |
| 85 | Online 7 |
| 87 | Online 8 |
