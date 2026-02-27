# Plan: Restructure TG-bot — menu + 3 roles

## Context
Current bot has a single 11-step FSM flow only for operators. Need to add a main menu with 3 scenarios: application (operator/agent/model), vacancy info, company info. The bot serves international candidates (PH, NG, LatAm) — all text in English.

## Architecture

**Current:**
```
/start → 11-step operator flow (candidate.py)
```

**Target:**
```
/start → Main Menu
  ├─ Apply Now → Role Selection
  │    ├─ Live Stream Operator → 11-step FSM (existing)
  │    ├─ Recruitment Agent → 6-step FSM (new)
  │    └─ Content Creator → 7-step FSM (new)
  ├─ About Vacancies → Info per role (with "Apply" shortcut)
  └─ About Company → Company info page
```

## Files to Create/Modify

### 1. NEW: `bot/handlers/menu.py` (~200 lines)
Entry point for all user-facing interactions. Replaces `/start` from candidate.py.

**MenuStates:**
- `main_menu` — user at main menu
- `role_select` — choosing role to apply
- `info_select` — choosing which role to read about

**Handlers:**
- `/start` → show main menu (3 inline buttons)
- `/menu` → return to menu from any state (no state filter)
- `callback "menu_apply"` → role selection (3 roles + Back)
- `callback "menu_vacancies"` → info selection (3 roles + Back)
- `callback "menu_company"` → company info + Back
- `callback "info_operator/agent/model"` → info page + "Apply" + "Back"
- `callback "role_operator"` → set candidate_type, transition to `OperatorForm.waiting_name`
- `callback "role_agent"` → set candidate_type, transition to `AgentForm.waiting_name`
- `callback "role_model"` → set candidate_type, transition to `ModelForm.waiting_name`
- `callback "back_main"` → clear state, show main menu (universal, no state filter)

### 2. NEW: `bot/handlers/operator_flow.py` (~350 lines)
Extract from `candidate.py` with minimal changes:
- Rename `ApplicationForm` → `OperatorForm`
- Remove `/start` handler (moved to menu.py)
- Keep all 11 steps + `_notify_admin` + `_send_to_n8n` intact
- Add `[OPERATOR]` prefix in admin notification
- Reuse existing: `hardware_checker`, `objection_handler`, `screener`, `followup`

### 3. NEW: `bot/handlers/agent_flow.py` (~180 lines)
6-step lighter flow for referral recruiters.

**AgentForm states:**
1. `waiting_name` — full name (free text)
2. `waiting_region` — inline: PH / NG / LatAm / Other
3. `waiting_english` — inline: same 5 options as operator
4. `waiting_experience` — recruiting experience (free text)
5. `waiting_hours` — inline: 5-10h/wk, 10-20h/wk, 20+h/wk
6. `waiting_contact` — TG/WhatsApp (free text)

**After completion:** No AI screening. Send formatted summary to admin with `agentok_` / `agentno_` buttons. Candidate gets "application received" message.

**Disqualifiers:** English < B1 → polite decline (same as operator).

### 4. NEW: `bot/handlers/model_flow.py` (~200 lines)
7-step flow for content creators.

**ModelForm states:**
1. `waiting_name` — full name (free text)
2. `waiting_age` — age (18+ required, same logic as operator)
3. `waiting_region` — inline: PH / NG / LatAm / RU-CIS / Other
4. `waiting_english` — inline: same 5 options (not a hard disqualifier for models)
5. `waiting_platform_experience` — streaming/content experience (free text)
6. `waiting_schedule` — inline: Morning / Day / Evening / Night / Flexible
7. `waiting_contact` — TG/WhatsApp (free text)

**After completion:** No AI screening. Send to admin with `modelok_` / `modelno_` buttons. Candidate gets "application received" message.

**Disqualifiers:** Age < 18 only.

### 5. MODIFY: `bot/handlers/admin.py` (+50 lines)
Add 4 callback handlers:
- `agentok_<user_id>` → approve agent, send welcome message
- `agentno_<user_id>` → reject agent, send polite decline
- `modelok_<user_id>` → approve model, send welcome message
- `modelno_<user_id>` → reject model, send polite decline

### 6. MODIFY: `bot/main.py` (~5 lines changed)
Update imports and router registration:
```python
from bot.handlers import admin, menu, operator_flow, agent_flow, model_flow

dp.include_router(admin.router)           # admin commands first
dp.include_router(menu.router)            # /start + menu + info + back_main
dp.include_router(operator_flow.router)   # operator FSM states
dp.include_router(agent_flow.router)      # agent FSM states
dp.include_router(model_flow.router)      # model FSM states
```

### 7. MODIFY: `bot/database/models.py` (+4 lines)
Add nullable columns to Candidate:
```python
recruiting_experience: Mapped[str | None] = mapped_column(Text, nullable=True)
available_hours: Mapped[str | None] = mapped_column(String(50), nullable=True)
platform_experience: Mapped[str | None] = mapped_column(Text, nullable=True)
preferred_schedule: Mapped[str | None] = mapped_column(String(100), nullable=True)
```

### 8. MODIFY: `bot/services/followup.py` (+50 lines)
Add greeting texts:
- `AGENT_GREETING` — agent welcome + payout info + "What is your full name?"
- `MODEL_GREETING` — model welcome + benefits + "What is your full name?"
- `APPLICATION_RECEIVED` — generic "thank you, we'll review within 24h"

### 9. DELETE: `bot/handlers/candidate.py`
Replaced by `menu.py` + `operator_flow.py`.

### 10. KEEP AS-IS: `bot/handlers/callbacks.py`
Remove from main.py router registration (no longer needed).

## Info Page Content

**Operator:** duties (OBS, chat mod, scheduling), pay ($150-400+/wk), training (5-7 days, $30/shift), schedule (5/2, 4 shifts), requirements (Windows PC, CPU/GPU specs, English B1+, 18+)

**Agent:** what you do (recruit operators/models), earnings per operator (1-3=$50, 4-6=$75, 7+=$100), earnings per model ($10/working day x 12mo), payment (USDT BEP20, weekly, min $50)

**Model:** content creation on streaming platforms, flexible schedule, training + mentor, revenue share, weekly payments, requirements (18+, internet)

**Company:** Apex Talent, international talent management, 15+ countries, 100% remote, weekly Sunday payments, no upfront fees, paid training from day 1

## Implementation Order

1. `bot/database/models.py` — add 4 columns
2. `bot/services/followup.py` — add greeting texts
3. `bot/handlers/menu.py` — create menu handler
4. `bot/handlers/operator_flow.py` — extract from candidate.py
5. `bot/handlers/agent_flow.py` — create agent flow
6. `bot/handlers/model_flow.py` — create model flow
7. `bot/handlers/admin.py` — add agent/model callbacks
8. `bot/main.py` — update router registration
9. Delete `bot/handlers/candidate.py`

## Verification
1. Run `python -c "from bot.handlers import menu, operator_flow, agent_flow, model_flow"` — imports work
2. Run `python -m bot.main` — bot starts without errors
3. Test `/start` → main menu appears with 3 buttons
4. Test Apply → Operator → full 11-step flow works
5. Test Apply → Agent → 6-step flow, admin gets notification
6. Test Apply → Model → 7-step flow, admin gets notification
7. Test info pages → correct content, "Apply" and "Back" buttons work
8. Test `/menu` → returns to menu from any state
9. Test admin approve/reject buttons for all 3 roles
