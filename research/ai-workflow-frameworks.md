# Как топы работают с AI: фреймворки и методы

> Исследование: март 2026. Источники: Twitter/X, блоги, подкасты.
> Фокус: workflow с AI-кодинг ассистентами (Claude Code, Cursor, Codex)

---

## Проблема, которую все решают

**Context switching hell** — AI подталкивает к мультизадачности:
- Запустил задачу в одном чате → пока ждёшь → прыгаешь в другой
- Контекст проекта в голове, а не в системе
- Потеря фокуса, сложно планировать, "многозадачность" без системы
- Каждый чат теряет контекст при переключении

**Ключевой инсайт из индустрии:** проблема не в инструментах, а в том что люди используют AI как "чат, который нужно бебиситтить" вместо "параллельное исполнение, которое ты проверяешь когда нужно суждение" (Boris Cherny)

---

## Фреймворк 1: «Параллельный Конвейер» (Boris Cherny, создатель Claude Code)

**Источник:** [Threads](https://threads.com/@boris_cherny), [X](https://x.com/bcherny), Medium-разбор от Faraz Aulia

### Философия
> "Parallelism over speed" — не быстрее кодить, а больше делать одновременно

### Структура
```
5 git worktrees × 5 Claude сессий = 5 параллельных задач
+ 5-10 сессий в браузере (web Claude)
= 10-15 агентов одновременно
```

### 10 привычек команды Claude Code

1. **Параллельные worktrees** — главный unlock продуктивности
   - Каждая сессия в своём изолированном чекауте
   - Пока один агент "думает" → переключаешься на другой
   - Мёртвое время становится продуктивным

2. **Plan Mode по умолчанию** — для всего нетривиального
   - Сначала план → потом реализация за один проход
   - Claude A пишет план, Claude B ревьюит (свежий контекст)

3. **CLAUDE.md как компаунд-актив** — после каждой ошибки:
   - "Update CLAUDE.md so you don't make that mistake again"
   - Со временем — агрессивный прунинг, пока частота ошибок не упадёт

4. **Skills = повторяемые действия** — если делаешь >1 раза в день → навык
   - `/techdebt` — поиск лёгких улучшений
   - `/commit-push-pr` — стейдж → коммит → пуш → PR → URL

5. **Баг-фиксинг: сырой контекст + "fix"** — не микроменеджить
   - Дать CI output, логи, Slack-тред → Claude сам разберётся

6. **Промптинг: challenge → prove → elegant**
   - "Grill me on these changes" (Claude как ревьюер)
   - "Prove to me this works" (тесты, логи, диффы)
   - "Knowing everything you know now, implement the elegant solution"

7. **Терминал: таб на задачу** — Ghostty/tmux, statusline с контекстом

8. **Субагенты для чистого контекста** — тяжёлые операции (тесты, поиск)
   делегировать субагентам, основной контекст остаётся чистым

9. **Claude для аналитики** — через CLI/MCP к БД

10. **Claude для обучения** — ask for explanations, diagrams, presentations

### Ключевой принцип
> ".claude/ директория коммитится в git → знания команды компаундятся"

---

## Фреймворк 2: «Хирург» (Geoffrey Litt, MIT/Ink & Switch)

**Источник:** [geoffreylitt.com/2025/10/24/code-like-a-surgeon](https://www.geoffreylitt.com/2025/10/24/code-like-a-surgeon)

### Метафора
Хирург ≠ менеджер. Хирург **делает** работу, но его время максимально leverage'ится командой поддержки (подготовка, вторичные задачи, администрирование).

### Структура: Primary vs Secondary tasks

| | Primary (ты делаешь) | Secondary (AI делает) |
|---|---|---|
| **Что** | Дизайн-решения, архитектура, UX | Гайды по кодбейзу, спайки, фиксы TS-ошибок, документация |
| **Когда** | Синхронно, в фокусе | Асинхронно, фоном (во время обеда, ночью) |
| **Автономия AI** | Низкая (AI = copilot) | Высокая (AI = автономный агент) |
| **Результат** | Код идёт в прод | Черновик для ревью / контекст |

### Slider автономии
```
Copilot mode ◀━━━━━━━━━━━━━━━━━▶ Agent mode
(ты рулишь)                    (AI рулит)

Primary tasks ← левая часть
Secondary tasks ← правая часть
```

### Ритуал
> "When I sit down for a work session, I want to feel like a surgeon walking into a prepped operating room. Everything is ready for me to do what I'm good at."

**Подготовка (AI делает заранее):**
- Написать гайд по релевантным частям кодбейза
- Сделать спайк (черновой подход, не для прода — для понимания)
- Пофиксить очевидные баги
- Написать документацию

---

## Фреймворк 3: «Мульти-инструментальный конвейер» (Twitter consensus)

### Паттерн (Sankalp @dejavucoder, Matthew @0xDeltaHedged и др.)

Разные AI-инструменты для разных фаз:

```
PLANNING          BUILDING           REVIEW
   │                  │                │
   ▼                  ▼                ▼
Claude Chat      Cursor / Claude   Cursor / Claude
(codebase Q&A,    Code (features,     (code review,
 prompt eng)      bug fixes)          experiments)
                      │
                      ▼
                   Codex
              (background tasks,
               autonomous work)
```

### Mark Essien (@markessien, Hotels.ng)
> "One AI for coding, one for planning new features, one for auditing those plans"

Три параллельных контекста:
1. **Coding AI** — пишет код
2. **Planning AI** — генерирует идеи фич
3. **Audit AI** — проверяет планы Planning AI

---

## Фреймворк 4: «PRD-Driven Development» (GitHub, @bibryam)

**Источник:** GitHub official (@github), Bilgin Ibryam

### Принцип
> "Vibe coding might feel good, but actually achieving results requires **structured context and detailed specifications**"

### Структура
1. **PRD (Product Requirement Document)** перед каждой крупной задачей
2. **Планирование** — подробный разбор на шаги
3. **Инкрементальная реализация** — маленькие итерации
4. **Верификация** на каждом шаге (тесты, проверки)

### Процесс @potrepka (5 шагов Claude Code)
1. Scope — определить размер задачи (маленький)
2. Plan — детально с AI
3. Implement — один проход
4. Review — внимательно вычитать сгенерированный код
5. Test — убедиться что работает

---

## Фреймворк 5: «Context is King» (Will Dyess, Memo MCP)

### Проблема
Context window = главный ресурс. Когда он забивается — качество падает.

### Решения

**Will Dyess** (8 месяцев экспериментов):
- Управление контекстом — самый важный навык работы с AI
- Короткие, целенаправленные сессии (не один мегачат на всё)
- Регулярный /compact или новый чат

**Memo MCP** (@BadTechBandit):
- Инструмент для сохранения контекста между AI-инструментами
- Переключаешься Claude → Cursor → обратно без потери контекста

**Filipe Nevola** (@FilipeNevola):
- Claude и Cursor автономно обновляют инструкции друг друга
- AI-инструменты управляют AI-инструментами

---

## Синтез: рекомендуемая система для соло-фаундера

### Уровень 1: Планирование (утро, 30 мин)

```
УТРО: Eisenhower + 1-3-5
┌─────────────────────────┐
│ 1 Big Thing (Q2 важное) │ ← Стратегическая работа
│ 3 Medium Things         │ ← Текущий спринт
│ 5 Small Things          │ ← Quick wins, баги
└─────────────────────────┘
          ↓
    TickTick / Kanban
    (задачи с тайм-блоками)
```

### Уровень 2: Исполнение (рабочий день)

```
РЕЖИМ ХИРУРГА:
┌──────────────────────────────────────┐
│ 1. PREP (AI делает фоном/заранее)   │
│    - Ресёрч, спайки, гайды          │
│    - Субагенты на вторичные задачи   │
│                                      │
│ 2. FOCUS (ты делаешь, AI = copilot) │
│    - 90-мин блоки без переключений  │
│    - Plan Mode → 1 проход           │
│    - Одна задача = один чат          │
│                                      │
│ 3. REVIEW (ты + AI)                 │
│    - "Prove it works"               │
│    - Тесты, /ship                   │
│                                      │
│ 4. SWITCH (конвейер)                │
│    - Следующая задача из TickTick    │
│    - Новый чат / worktree           │
└──────────────────────────────────────┘
```

### Уровень 3: Инструменты

| Функция | Инструмент |
|---------|-----------|
| Планирование спринта | Claude Code + TickTick |
| Kanban / трекинг | TickTick (списки = колонки) |
| Фокус-сессия (primary) | Claude Code в VS Code (один чат = одна задача) |
| Фоновые задачи (secondary) | Claude Code в терминале (worktree) или Codex |
| Контекст проекта | CLAUDE.md + knowledge/ |
| Ежедневный обзор | TickTick + утренний ритуал |

### Правила против хаоса

1. **Один чат = одна задача.** Не мешать контексты
2. **Контекст в файлах, не в голове.** CLAUDE.md, TickTick, knowledge/
3. **Фоновые задачи ≠ параллельные.** Запустил и забыл, не переключайся
4. **90 минут фокуса → перерыв.** Не прыгать между чатами
5. **Plan Mode для нетривиального.** Потратить 5 мин на план = сэкономить 30 на переделках
6. **Утренний ритуал.** Посмотреть TickTick → определить Big Thing → начать с него
7. **Вечерний закрытие.** Что сделано → что на завтра → обновить CLAUDE.md

---

## Источники

- Boris Cherny (создатель Claude Code): [X thread](https://x.com/bcherny/status/2017742741636321619), [Threads](https://threads.com/@boris_cherny)
- Geoffrey Litt: [Code like a surgeon](https://www.geoffreylitt.com/2025/10/24/code-like-a-surgeon)
- Faraz Aulia: [10 Best Practices from Claude Code team](https://medium.com/@rub1cc/how-claude-codes-creator-uses-it-10-best-practices-from-the-team-e43be312836f)
- self.md: [Boris Cherny's Parallel Agent Workflow](https://self.md/people/boris-cherny-claude-code/)
- vibecodedthis.com: [Claude Code Git Worktree Support](https://vibecodedthis.com/blog/claude-code-git-worktree-support-boris-cherny/)
- @markessien, @dejavucoder, @potrepka, @WillDyess, @quionie — X/Twitter
- GitHub official: PRD-driven development
- Bilgin Ibryam: Addy Osmani's guide reference
