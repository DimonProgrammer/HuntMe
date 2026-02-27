# HuntMe — Infrastructure & Technical Reference

> Last updated: 2026-02-27. Keep this file updated when architecture changes.

---

## Stack

| Layer | Technology | Where |
|---|---|---|
| Bot | Python 3.11 + aiogram 3.x | Render (apex-talent-bot.onrender.com) |
| Landing | HTML/CSS/JS static | Vercel (apextalent.pro) |
| Database | Neon PostgreSQL (Singapore) | aws-ap-southeast-1 |
| FSM storage | PostgreSQL (`fsm_states` table) | Same Neon DB |
| AI screening | Groq llama-3.3-70b-versatile | api.groq.com |
| CRM | HuntMe CRM (huntmecrm.com) | External, session token |
| Leads tracking | Notion DB | Internal Integration Token |
| Live chat | Chatwoot Cloud (app.chatwoot.com) | Account 153965, Inbox 98089 |
| Live feed | Telegram channel | LIVE_FEED_CHANNEL_ID env var |
| Monitoring | UptimeRobot → /healthz every 5 min | Keeps Render free tier alive |

---

## Environment Variables (Render)

```
BOT_TOKEN                 — Telegram bot token (@apextalent_bot)
ADMIN_CHAT_ID             — Admin's Telegram numeric ID
DATABASE_URL              — Neon PostgreSQL connection string (pooler)
GROQ_API_KEY              — Groq API key (only working AI)
NOTION_TOKEN              — Notion Internal Integration Token
NOTION_LEADS_DB_ID        — 237a3a0a251941b3973c74212d6a6ee8
LIVE_FEED_CHANNEL_ID      — Telegram channel for live mirroring
HUNTME_CRM_LOGIN          — CRM login email
HUNTME_CRM_PASSWORD       — CRM password
CHATWOOT_BASE_URL         — https://app.chatwoot.com
CHATWOOT_API_TOKEN        — qjY8Zr56XZk3Zbhd7zrZAdye
CHATWOOT_ACCOUNT_ID       — 153965
CHATWOOT_INBOX_ID         — 98089
CHATWOOT_BOT_AGENT_ID     — 163922
PORT                      — 10000
```

Non-working (don't add): GEMINI_API_KEY (regional quota=0), OPENROUTER_API_KEY (401 invalid).

---

## Database Schema

### `candidates`
Core table. One row per applicant.

| Column | Type | Notes |
|---|---|---|
| id | int PK | Auto-increment |
| tg_user_id | bigint UNIQUE | Set when candidate enters bot |
| tg_username | varchar | @handle without @ |
| name | varchar | Full name from screening |
| region | varchar | 'cis' for RU, otherwise from answers |
| language | varchar(5) | 'en' or 'ru' |
| platform | varchar | 'landing', 'telegram', etc. |
| candidate_type | varchar | Always 'operator' |
| status | varchar(30) | See status lifecycle below |
| score | int | AI screening score 0–100 |
| recommendation | varchar | PASS / MAYBE / REJECT |
| notes | text | AI reasoning |
| english_level | varchar | Beginner / B1 / B2 / C1 |
| study_status | varchar | student_inperson / working / etc. |
| pc_confidence | varchar | Self-rated level |
| cpu_model | varchar | Full model name |
| gpu_model | varchar | Full model name |
| hardware_compatible | bool | NULL = not checked |
| internet_speed | varchar | e.g. "100 Mbps" |
| start_date | varchar | When can start |
| birth_date | varchar | dd.MM.yyyy (for CRM) |
| phone_number | varchar | Digits only |
| phone_country | varchar(5) | 'ph', 'id', 'ng', 'ru', etc. |
| experience | text | Free-text from booking flow |
| huntme_crm_slot | varchar(20) | 'dd.MM.yyyy HH:mm' — locked slot |
| huntme_crm_submitted | bool | True after successful CRM submit |
| interview_morning_sent | bool | Morning reminder sent |
| interview_reminder_sent | bool | 1h reminder sent |
| contact_info | varchar | Provided contact (TG/WA/email) |
| referrer_tg_id | bigint | Who referred this candidate |
| utm_source | varchar | 'landing', 'referral', etc. |

**Candidate status lifecycle:**
```
new → in_bot → screened → pending_crm_approval → interview_invited → active / churned
                ↑                  ↓
           (re-apply)          declined
```

### `slot_reservations`
Temporary locks during booking flow (30-min TTL).

| Column | Type | Notes |
|---|---|---|
| slot_str | varchar(20) PK | 'dd.MM.yyyy HH:mm' |
| tg_user_id | bigint | Who holds this slot |
| reserved_at | timestamp | For expiry calculation |

Slot is freed when: admin approves, admin rejects, candidate re-picks, 30 min expires.

### `chatwoot_mappings`
Maps Telegram user IDs to Chatwoot contacts/conversations.

| Column | Type | Notes |
|---|---|---|
| tg_user_id | bigint PK | Telegram user ID |
| contact_id | int | Chatwoot contact ID |
| conversation_id | int | Chatwoot conversation ID |
| created_at | timestamp | |

### `fsm_states`
FSM persistence (PostgresStorage). Stores aiogram state as JSON.

### `funnel_events`
Analytics events (step, event_type, timestamp per candidate).

---

## Request / Message Flow

### 1. Landing Lead Flow
```
User fills form (apextalent.pro)
  → POST /webhook/landing
  → Creates Candidate(status=pending_bot, tg_user_id=NULL)
  → Notifies admin with deep link
  → 30-min timer: if still pending_bot → remind admin

User clicks deep link (t.me/apextalent_bot?start=land_42)
  → menu.py: _handle_landing_deeplink()
  → Links tg_user_id to existing Candidate row
  → Skips name question (already known)
  → Starts screening at waiting_has_pc
```

### 2. Direct Bot Flow
```
User sends /start
  → menu.py: on_start()
  → Creates Notion lead entry
  → Sends WARM_GREETING (with name question)
  → operator_flow.py takes over (waiting_name state)
```

### 3. Screening Flow (operator_flow.py)
11 FSM steps:
1. `waiting_name` — full name
2. `waiting_has_pc` — do you have a PC?
3. `waiting_age` — age (18+ check)
4. `waiting_study` — study/work status
5. `waiting_english` — English level
6. `waiting_pc_confidence` — PC confidence
7. `waiting_cpu` — CPU model (or simplified path)
8. `waiting_gpu` — GPU model (or simplified path)
9. `waiting_internet` — internet speed
10. `waiting_start_date` — when can you start
11. `waiting_contact` — contact info (TG/WA/email)

After step 11:
- AI screening via Groq (llama-3.3-70b-versatile)
- `_save_candidate()` → saves to Neon + updates Notion
- PASS → `start_booking()` (interview_booking.py)
- MAYBE/REJECT → notify admin with Interview/Reject buttons

### 4. Booking Flow (interview_booking.py)
```
start_booking()
  → waiting_birth_date → waiting_phone → waiting_experience
  → _show_slots() — fetches from CRM, filters reserved/expired
  → Candidate picks slot → _try_reserve_slot() (race protection)
  → _request_crm_approval() — saves to DB, sends admin preview
  → Candidate sees BOOKING_SLOT_CHOSEN + [Change slot] button
  → State: waiting_crm_approval (kept, not cleared)

Admin sees CRM SUBMISSION card:
  [✅ Approve & Submit]  [❌ Reject]

On Approve:
  → Verify slot still exists in CRM
  → generate_crm_answers() via AI
  → submit_application() to HuntMe CRM
  → status → interview_invited, huntme_crm_submitted=True
  → Send BOOKING_INVITE to candidate (+ Google Calendar link)
  → Release slot_reservation

On Reject:
  → status → screened, huntme_crm_slot=NULL
  → Release slot_reservation
  → Send BOOKING_SOFT_REJECT to candidate

Candidate clicks [Change slot] (before approval):
  → Release slot_reservation
  → status → screened, huntme_crm_slot=NULL
  → Re-show slot picker
```

### 5. Chatwoot Mirroring Flow
```
Any candidate message →
  LiveFeedMiddleware.mirror_incoming()
    → get_or_create_conversation(tg_user_id)
      → POST /contacts (or search if 422)
      → POST /conversations with inbox_id=98089
      → Save chatwoot_mappings(tg_user_id, contact_id, conv_id)
    → POST /conversations/{id}/messages (type=incoming)

Bot sends message to candidate →
  LoggingBot.send_message() →
    chatwoot_client.mirror_outgoing()
      → Lookup conv_id from chatwoot_mappings
      → POST /conversations/{id}/messages (type=outgoing)

Admin replies in Chatwoot UI →
  POST /webhook/chatwoot (our server)
    → Filter: message_type=1 (outgoing), skip bot_agent_id
    → conversation_to_tg_user(conv_id) → tg_user_id
    → bot.send_message(tg_user_id, content)
```

### 6. Interview Day Reminders (reminder.py)
Background task checks every 60 seconds:
- Finds candidates: `status=interview_invited, huntme_crm_submitted=True`
- **Morning reminder** (09:00 Manila): sent if slot is >1h away, `interview_morning_sent=False`
  - Buttons: [✅ I'll be there!] [❌ Can't make it]
- **1h reminder**: sent 1h before slot, `interview_reminder_sent=False`

---

## HuntMe CRM Integration

**Auth:** NextAuth v5 session cookie (`__Secure-authjs.session-token`)
- Token cached in `_SESSION_TOKEN` module variable
- Auto re-login on 401/403
- Token lifespan: ~30 days
- CloudFront in front — requires realistic User-Agent

**Key endpoints used:**
- `GET /api/trpc/candidate.getAvailableTime` — available slots
- `POST /api/trpc/candidate.createCandidate` — submit application
- Form: multipart/form-data (NOT JSON), office_id=95
- Question IDs: 49 (English), 50 (Study), 51 (PC confidence), 52 (Experience)

**Slot format:** `dd.MM.yyyy HH:mm` (Manila timezone, UTC+8)

**Filtering:** Sundays skipped, past hours for today filtered

---

## AI Screening (claude_client.py / screener.py)

**AI fallback chain:** Groq → Gemini → OpenRouter → Anthropic
**Working:** Only Groq (llama-3.3-70b-versatile). Others fail due to regional/key issues.

Screening returns `ScreeningResult`:
- `overall_score` (0–100)
- `recommendation` (PASS / MAYBE / REJECT)
- `english_score`, `hardware_score`, `availability_score`, `motivation_score`, `experience_score`
- `reasoning`, `suggested_response`

AI fallback (if all fail): `overall_score=0, recommendation=MAYBE`.

---

## Router Registration Order (main.py)

Order matters — first match wins:
```python
dp.include_router(admin.router)          # Admin commands + reply handler (priority)
dp.include_router(interview_booking.router)  # CRM FSM states
dp.include_router(menu.router)           # /start, /menu, info pages
dp.include_router(operator_flow.router)  # Screening FSM states
```

---

## Known Issues / Gotchas

| # | Severity | Issue | Status |
|---|---|---|---|
| 1 | ✅ Fixed | Chatwoot contact ID parsing (nested payload.contact.id) | Fixed 2026-02-27 |
| 2 | ✅ Fixed | Chatwoot search returns list not dict (AttributeError) | Fixed 2026-02-27 |
| 3 | ✅ Fixed | Chatwoot middleware tied to LIVE_FEED_CHANNEL_ID | Fixed 2026-02-27 |
| 4 | ✅ Fixed | Stale slots (past hours shown for today) | Fixed 2026-02-27 |
| 5 | ✅ Fixed | Race condition: two users pick same slot | Fixed (SlotReservation) |
| 6 | ✅ Fixed | Admin CRM card shows N/A (DB fallback to FSM data) | Fixed 2026-02-27 |
| 7 | ⚠️ Monitor | CRM token ~30 days, auto re-login on 401 only | Watch for silent failures |
| 8 | ⚠️ Monitor | CRM question_ids (49-52) tied to office_id=95 | Re-check if office changes |
| 9 | ℹ️ Known | Gemini/OpenRouter don't work (regional/key issues) | Groq is sole AI |
| 10 | ℹ️ Known | Landing leads get duplicate DB row if they re-submit form | Low impact, no unique constraint on landing |
| 11 | ℹ️ Known | Phone country detection: +7 → 'ru' (also KZ/BY) | Acceptable for current markets |

---

## Deployment

**Bot (Render):**
- Auto-deploy on push to `main`
- Service: `apex-talent-bot`
- Start command: `python -m bot.main`
- Health check: `GET /healthz` → "ok"
- UptimeRobot pings every 5 min to prevent sleep

**Landing (Vercel):**
- Auto-deploy on push to `main`
- `landing/index.html` → apextalent.pro (EN)
- `landing/ru/index.html` → apextalent.pro/ru (RU)
- Form posts to: `https://apex-talent-bot.onrender.com/webhook/landing`

**Webhooks served by bot:**
- `POST /webhook/landing` — landing form submissions
- `POST /webhook/chatwoot` — Chatwoot outgoing replies
- `GET /healthz` — health check

---

## Bilingual Support

All user-facing text in `bot/messages/`:
- `en.py` — English (universal, for PH/ID/NG)
- `ru.py` — Russian (CIS market)

Language set from:
1. Deep link prefix: `land_ru_*` → Russian, `land_*` → English
2. Telegram locale if no deep link
3. Default: English

**Rule:** All content changes must be made in BOTH files simultaneously.

---

## Notion Leads DB

**DB ID:** `237a3a0a251941b3973c74212d6a6ee8`

Events tracked per candidate:
- `on_start` — bot started (source, TG handle)
- `on_name` — name captured
- `on_complete` — screening done (score, recommendation, all answers)

Failures are logged but not escalated (silent).

---

## Monitoring Checklist

- [ ] Render logs: check for ERROR lines after each deploy
- [ ] Chatwoot: conversations appearing for new candidates
- [ ] Neon: `chatwoot_mappings` count growing
- [ ] CRM: check `huntme_crm_submitted=True` candidates have CRM entries
- [ ] Groq: watch for rate limit errors in logs
- [ ] UptimeRobot: bot responding to /healthz
