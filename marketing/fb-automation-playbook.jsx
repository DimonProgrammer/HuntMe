import { useState } from "react";

const sections = [
  {
    id: "overview",
    icon: "🎯",
    title: "Обзор ситуации",
    color: "#FF6B35",
    content: {
      intro: "Meta убила Groups API в апреле 2024 — Hootsuite, Buffer, MeetEdgar и все остальные потеряли возможность постить в группы. Остались только инструменты на базе браузерной автоматизации.",
      keyPoints: [
        { label: "Что работает", text: "Только browser automation — симуляция действий реального человека в браузере" },
        { label: "Бюджет", text: "От $100/мес (малый масштаб) до $3,500/мес (200+ групп)" },
        { label: "Потери аккаунтов", text: "15–30% аккаунтов банятся ежемесячно — это нормальная «стоимость ведения бизнеса»" },
        { label: "Воронка", text: "Пост в группе → Комментарий/ДМ → ManyChat на Page → Telegram-бот (уже есть)" },
      ],
    },
  },
  {
    id: "tools",
    icon: "🛠",
    title: "Инструменты постинга",
    color: "#4ECDC4",
    content: {
      intro: "Все работающие инструменты нарушают ToS Facebook — «безопасного» автопостинга в группы не существует. Есть только степени управления рисками.",
      tools: [
        { name: "PilotPoster", price: "$9.99/мес", mechanism: "Браузерная автоматизация", reliability: "Высокая", risk: "Средний", note: "Лидер рынка, 1.5M+ постов/мес, spintax, задержки 2–5 мин", recommended: true },
        { name: "FB Group Bulk Poster", price: "$8.99/мес", mechanism: "Chrome-расширение", reliability: "Высокая", risk: "Средний", note: "4,000+ юзеров, 4.9★, данные не уходят на сервер", recommended: true },
        { name: "MaherPost", price: "$37/мес", mechanism: "Браузерная автоматизация", reliability: "Высокая", risk: "Средний", note: "Авто-вступление в группы, встроенная защита от банов" },
        { name: "Socinator", price: "$10–175/мес", mechanism: "Десктоп-софт", reliability: "Средняя", risk: "Высокий", note: "Мультиплатформа (9+ соцсетей), но отзывы смешанные" },
        { name: "FS Poster", price: "$45 разово", mechanism: "Cookie-метод", reliability: "~70%", risk: "Средний", note: "WordPress-плагин, каждый 3й пост может не пройти" },
      ],
    },
  },
  {
    id: "comments",
    icon: "💬",
    title: "Автоматизация ответов",
    color: "#7B68EE",
    content: {
      intro: "Критический момент: ни один инструмент не может автоматически отвечать на комменты внутри групп. ManyChat, Chatfuel и другие работают только с контентом вашей Facebook Page.",
      funnel: [
        { step: 1, action: "Пост в группе", tool: "PilotPoster / FB Group Bulk Poster", detail: "Браузерная автоматизация, spintax для вариаций" },
        { step: 2, action: "CTA → ваша Page", tool: "Текст поста", detail: "Направляем на комментарий под постом Page или m.me/YourPage" },
        { step: 3, action: "Авто-ДМ в Messenger", tool: "ManyChat Pro ($15/мес)", detail: "Ловим ключевое слово (APPLY), шлём ДМ с ссылкой на бота" },
        { step: 4, action: "Логирование лида", tool: "Zapier / Make.com ($0–49/мес)", detail: "Запись в CRM, трекинг UTM-меток" },
        { step: 5, action: "Квалификация в Telegram", tool: "Ваш существующий бот", detail: "11-шаговая квалификация + AI-скрининг через Claude" },
      ],
      conversions: [
        { stage: "Просмотр → Отклик", rate: "2–10%" },
        { stage: "ДМ → Клик на Telegram", rate: "15–30%" },
        { stage: "Вход в бот → Завершение", rate: "40–70%" },
        { stage: "Итого: просмотр → квалиф. лид", rate: "0.5–3%" },
      ],
    },
  },
  {
    id: "philippines",
    icon: "🇵🇭",
    title: "Филиппины",
    color: "#FF4757",
    content: {
      stats: [
        { label: "Юзеров FB", value: "103M+" },
        { label: "Проникновение", value: "84% населения" },
        { label: "Время в FB", value: "23.5 ч/мес" },
        { label: "Зарплата стримера", value: "$100–3,000/мес" },
      ],
      groups: [
        "Work From Home Jobs Philippines (500K–1M+ участников)",
        "Online Filipino Freelancers / OFF (300K–500K+)",
        "Filipino Homebased Moms / FHMoms (350K+)",
        "Virtual Assistant Jobs Philippines (100K–500K+)",
        "Job Hiring Manila / Regional loker группы",
      ],
      language: "Taglish — микс тагальского и английского. Чистый English = холодно и корпоративно. Чистый Tagalog = дешёвая локальная работа. Пример: «HIRING: Live Streaming Operator (WFH) 🏠 | Gusto mo bang kumita ng $500–$800/month mula sa bahay?»",
      timing: "Лучшее время: 9–11 AM PHT (пик) и 7–9 PM PHT (вечер). Среда и пятница. 10 AM среда — рекорд по охвату.",
      trustSignals: [
        "GCash (~90% проникновение) — золотой стандарт",
        "Wise / PayPal для международных платежей",
        "«No application fees — we pay YOU»",
        "Сайт компании с SEC/DTI регистрацией",
        "Видео-отзывы от действующих работников",
        "Зарплата указана явно ($3–8/час entry)",
        "Видео-интервью (скамеры избегают видео)",
      ],
      scamWarning: "Жалобы на киберпреступления утроились (3,317 → 10,000+ за 2023–2024). 13.4% филиппинцев столкнулись с цифровым мошенничеством. DMW удалил 7,000+ нелегальных рекрутинговых постов из FB.",
    },
  },
  {
    id: "indonesia",
    icon: "🇮🇩",
    title: "Индонезия",
    color: "#FFA502",
    content: {
      stats: [
        { label: "TikTok Shop GMV", value: "$6.2B (2024)" },
        { label: "Live-покупки", value: "60% населения" },
        { label: "Зарплата хоста", value: "$95–1,070/мес" },
        { label: "Рынок", value: "2й в мире по TikTok Shop" },
      ],
      groups: [
        "Loker Jakarta / Loker Surabaya / Loker [город]",
        "Kerja Dari Rumah Indonesia",
        "Freelance Indonesia",
        "Info Loker Terbaru",
        "LOWONGAN INDONESIA (Telegram, 109K+ участников)",
      ],
      language: "WFH понятно всем. Заголовки на English, описание на Bahasa Indonesia. Полуформальный тон. Обращение «Kak» (гендерно-нейтральный уважительный формат). Ключевые слова: lowongan kerja, gaji, lamar sekarang, persyaratan.",
      timing: "Пик: 7–9 PM WIB (Джакарта). Вторичные: 7–9 AM и 12–1 PM. Избегать пятничной молитвы (~11:30–13:00). Ramadan и Eid — корректировать расписание.",
      trustSignals: [
        "Банки BCA, BRI, Mandiri, BNI — якоря доверия",
        "GoPay (71–88%), DANA (140–180M юзеров), OVO (80M+)",
        "Wise для международных фрилансеров",
        "«Tidak dipungut biaya» (без оплаты) — ОБЯЗАТЕЛЬНО",
        "Видео-интервью и живые отзывы",
      ],
      legalWarning: "Иностранные компании с удалёнными работниками из Индонезии рискуют создать BUT (Постоянное Представительство) → корпоративный налог 22%. Безопасный путь: независимые подрядчики с договором или EOR (Deel, Remote, Multiplier). Трудовые договоры должны быть на Bahasa Indonesia. Подоходный налог PPh 21: 5–35%.",
    },
  },
  {
    id: "security",
    icon: "🛡",
    title: "Антидетект и безопасность",
    color: "#2ED573",
    content: {
      intro: "Три столпа масштабного постинга без банов: антидетект-браузер (уникальный fingerprint), резидентные прокси (уникальный IP), прогрев аккаунтов (доверие перед постингом).",
      browsers: [
        { name: "GoLogin", price: "$24/мес (год)", profiles: "100", note: "Лучшее соотношение цена/качество, бесплатные встроенные прокси", recommended: true },
        { name: "AdsPower", price: "~$50/мес", profiles: "100", note: "Бесплатный no-code RPA для автоматизации, идеально для наших задач" },
        { name: "Multilogin", price: "€99/мес", profiles: "100", note: "Самый продвинутый, 2 движка (Chromium + Firefox), премиум прокси в комплекте" },
        { name: "Dolphin Anty", price: "~$89/мес", profiles: "100", note: "Заточен под FB/TikTok, встроенная FB-автоматизация" },
      ],
      proxies: [
        { name: "IPRoyal", price: "$1.75–3.50/ГБ", note: "Лучшая цена для PH + ID" },
        { name: "Smartproxy", price: "$3.00/ГБ", note: "Надёжный mid-range" },
        { name: "Bright Data", price: "$5–8.40/ГБ", note: "Премиум надёжность" },
        { name: "Oxylabs", price: "$4/ГБ", note: "4M индонезийских IP" },
      ],
      warming: [
        { week: "Неделя 1", actions: "Создание акка, уникальный телефон, фото, био. Листать ленту, лайкать 5–8 постов, добавить 5–10 друзей" },
        { week: "Неделя 2", actions: "2–3 заявки в друзья/день, 1–2 осмысленных комментария, вступить в 1–2 группы БЕЗ постинга" },
        { week: "Неделя 3", actions: "Лайки и комменты в группах (не посты)" },
        { week: "Неделя 4+", actions: "Начать постинг: 2–4 группы/день → постепенно до 4–8. Прогретые 3+ мес акки: до 10–20 групп/день (умеренный риск)" },
      ],
      contentRules: [
        "3–5 вариаций каждого поста через spintax",
        "Разные изображения (кроп, фильтр, другой текст)",
        "Ссылки — ТОЛЬКО в комментариях, не в посте",
        "Изображения/видео > текст (выше охват)",
        "Без сокращателей ссылок (триггерят спам-фильтр)",
        "FB тестирует лимит 2 ссылочных поста/мес для неверифицированных",
      ],
    },
  },
  {
    id: "budget",
    icon: "💰",
    title: "Бюджеты и стек",
    color: "#5352ED",
    content: {
      stack: [
        { component: "Постинг в группы", tool: "PilotPoster / FB Group Bulk Poster", cost: "$9–10" },
        { component: "Антидетект-браузер", tool: "GoLogin (годовой) / AdsPower", cost: "$24–50" },
        { component: "Резидентные прокси (PH+ID)", tool: "IPRoyal / Smartproxy", cost: "$18–120" },
        { component: "Авто-ответы на Page", tool: "ManyChat Pro", cost: "$15" },
        { component: "Telegram-бот", tool: "Существующий HuntMe бот", cost: "$0" },
        { component: "Интеграции", tool: "Zapier / Make.com", cost: "$0–20" },
        { component: "CRM (опционально)", tool: "GoHighLevel / HubSpot Free", cost: "$0–97" },
        { component: "VPN", tool: "Surfshark (2 года)", cost: "$2" },
      ],
      scales: [
        { scale: "Малый", groups: "10 групп", accounts: "3–5 акков", budget: "$100–220/мес", leads: "10–30 лидов/мес" },
        { scale: "Средний ✦", groups: "50 групп", accounts: "8–15 акков", budget: "$450–800/мес", leads: "50–150 лидов/мес" },
        { scale: "Большой", groups: "200+ групп", accounts: "25–50+ акков", budget: "$1,900–3,500/мес", leads: "200–500+ лидов/мес" },
      ],
      notes: [
        "Стоимость квалифицированного лида: ~$3–15",
        "VA для управления (4–6 ч/день): +$200–500/мес",
        "Запасные аккаунты: всегда держать +20–30% сверху",
        "Покупка aged-акков: $10–50/штука",
        "Виртуальные номера PH/ID: $0.10–0.50/номер",
      ],
    },
  },
  {
    id: "roadmap",
    icon: "🚀",
    title: "План запуска",
    color: "#FF6348",
    content: {
      phases: [
        {
          phase: "Фаза 1",
          period: "Недели 1–2",
          title: "Инфраструктура",
          tasks: [
            "Настроить GoLogin / AdsPower с 5–10 профилями",
            "Купить резидентные прокси с IP Филиппин и Индонезии",
            "Приобрести 5–10 aged-аккаунтов, начать прогрев",
            "Создать бизнес-Page для Apex Talent (лого, сайт, отзывы, контент)",
            "Подключить ManyChat Pro → построить flow с keyword-триггерами (APPLY, INTERESTED)",
          ],
        },
        {
          phase: "Фаза 2",
          period: "Недели 3–4",
          title: "Контент и подготовка групп",
          tasks: [
            "Создать 3–5 вариаций постов для каждой роли на Taglish (PH) и Bahasa/English (ID)",
            "Дизайн брендированных график в Canva (лого Apex Talent)",
            "Вступить в 20–50 целевых групп через прогретые аккаунты",
            "Неделю только engagement в группах: лайки, комменты — БЕЗ постов",
          ],
        },
        {
          phase: "Фаза 3",
          period: "Неделя 5+",
          title: "Запуск и оптимизация",
          tasks: [
            "Начать постинг: 4–8 групп на аккаунт в день",
            "Филиппины: 9–11 AM PHT | Индонезия: 7–9 PM WIB",
            "Уникальные deep-links для трекинга: t.me/Bot?start=ph_wfh_group1",
            "Мониторинг shadow-банов (резкое падение engagement → переход на резервный акк)",
          ],
        },
        {
          phase: "Фаза 4",
          period: "Постоянно",
          title: "Масштабирование",
          tasks: [
            "Непрерывный прогрев новых аккаунтов для замены забаненных",
            "A/B тесты вариаций постов, CTA и тайминга",
            "Трекинг cost-per-lead по группам и странам → фокус на лучших",
            "Рассмотреть FB Lead Ads как дополнение (SEA = на 50–75% дешевле Запада)",
          ],
        },
      ],
    },
  },
];

const riskMatrix = [
  { risk: "Бан аккаунта", probability: "Высокая", impact: "Средний", mitigation: "Пул запасных аккаунтов (+20–30%), антидетект-браузер, прогрев 2–4 недели" },
  { risk: "Shadow-бан (посты не видны)", probability: "Высокая", impact: "Высокий", mitigation: "Мониторинг engagement, ротация аккаунтов, разнообразие контента через spintax" },
  { risk: "Бан из группы админом", probability: "Средняя", impact: "Низкий", mitigation: "Человечные посты без спам-маркеров, engagement до постинга, уважение правил группы" },
  { risk: "Связывание аккаунтов (coordinated activity)", probability: "Средняя", impact: "Критический", mitigation: "Уникальные IP и fingerprint на каждый акк, никогда не копипастить один текст" },
  { risk: "Юр. риск в Индонезии (BUT)", probability: "Низкая", impact: "Критический", mitigation: "Contractor agreement, EOR (Deel/Remote), договоры на Bahasa Indonesia" },
  { risk: "Обвинения в скаме от кандидатов", probability: "Средняя", impact: "Высокий", mitigation: "Trust signals: GCash/DANA, видео-отзывы, сайт, SEC-регистрация, «No fees»" },
  { risk: "Слом инструмента (FB обновил UI)", probability: "Средняя", impact: "Средний", mitigation: "2–3 инструмента в арсенале, ручной backup-процесс" },
];

function Badge({ children, color }) {
  return (
    <span style={{ background: color + "22", color: color, padding: "3px 10px", borderRadius: "6px", fontSize: "12px", fontWeight: 600, letterSpacing: "0.3px" }}>
      {children}
    </span>
  );
}

function RiskBadge({ level }) {
  const colors = { "Высокая": "#FF4757", "Средняя": "#FFA502", "Низкая": "#2ED573", "Критический": "#FF0040", "Высокий": "#FF4757", "Средний": "#FFA502", "Низкий": "#2ED573" };
  return <Badge color={colors[level] || "#999"}>{level}</Badge>;
}

function ToolCard({ tool, recommended }) {
  return (
    <div style={{
      background: recommended ? "linear-gradient(135deg, #1a1a2e, #16213e)" : "#141420",
      border: recommended ? "1px solid #4ECDC466" : "1px solid #ffffff10",
      borderRadius: "12px",
      padding: "16px",
      position: "relative",
      overflow: "hidden"
    }}>
      {recommended && (
        <div style={{ position: "absolute", top: "8px", right: "8px", background: "#4ECDC4", color: "#000", fontSize: "10px", fontWeight: 700, padding: "2px 8px", borderRadius: "4px", textTransform: "uppercase", letterSpacing: "0.5px" }}>
          Рекомендую
        </div>
      )}
      <div style={{ fontSize: "16px", fontWeight: 700, color: "#fff", marginBottom: "4px" }}>{tool.name}</div>
      <div style={{ fontSize: "20px", fontWeight: 800, color: "#4ECDC4", marginBottom: "8px" }}>{tool.price}</div>
      <div style={{ fontSize: "12px", color: "#ffffff80", marginBottom: "8px" }}>
        <span style={{ marginRight: "12px" }}>⚙ {tool.mechanism}</span>
        <span style={{ marginRight: "12px" }}>✓ {tool.reliability}</span>
        <span>⚠ Риск: {tool.risk}</span>
      </div>
      <div style={{ fontSize: "13px", color: "#ffffffbb", lineHeight: 1.5 }}>{tool.note}</div>
    </div>
  );
}

function FunnelStep({ step, isLast }) {
  return (
    <div style={{ display: "flex", alignItems: "flex-start", gap: "14px", position: "relative" }}>
      <div style={{ display: "flex", flexDirection: "column", alignItems: "center", minWidth: "36px" }}>
        <div style={{ width: "36px", height: "36px", borderRadius: "50%", background: "linear-gradient(135deg, #7B68EE, #5352ED)", display: "flex", alignItems: "center", justifyContent: "center", color: "#fff", fontWeight: 800, fontSize: "14px", flexShrink: 0 }}>
          {step.step}
        </div>
        {!isLast && <div style={{ width: "2px", height: "40px", background: "#7B68EE33", marginTop: "4px" }} />}
      </div>
      <div style={{ paddingBottom: isLast ? 0 : "16px" }}>
        <div style={{ fontWeight: 700, color: "#fff", fontSize: "14px" }}>{step.action}</div>
        <div style={{ fontSize: "12px", color: "#7B68EE", fontWeight: 600, marginTop: "2px" }}>{step.tool}</div>
        <div style={{ fontSize: "13px", color: "#ffffff88", marginTop: "2px" }}>{step.detail}</div>
      </div>
    </div>
  );
}

function CountryStats({ stats, color }) {
  return (
    <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "10px", marginBottom: "20px" }}>
      {stats.map((s, i) => (
        <div key={i} style={{ background: color + "15", borderRadius: "10px", padding: "14px", borderLeft: `3px solid ${color}` }}>
          <div style={{ fontSize: "11px", color: "#ffffff66", textTransform: "uppercase", letterSpacing: "0.5px", marginBottom: "4px" }}>{s.label}</div>
          <div style={{ fontSize: "18px", fontWeight: 800, color: "#fff" }}>{s.value}</div>
        </div>
      ))}
    </div>
  );
}

export default function FBAutomationPlaybook() {
  const [activeSection, setActiveSection] = useState("overview");
  const [showRisks, setShowRisks] = useState(false);

  const section = sections.find((s) => s.id === activeSection);

  const renderContent = () => {
    if (!section) return null;
    const c = section.content;

    switch (section.id) {
      case "overview":
        return (
          <div>
            <p style={{ fontSize: "15px", color: "#ffffffcc", lineHeight: 1.7, marginBottom: "24px" }}>{c.intro}</p>
            <div style={{ display: "flex", flexDirection: "column", gap: "12px" }}>
              {c.keyPoints.map((p, i) => (
                <div key={i} style={{ background: "#ffffff08", borderRadius: "10px", padding: "16px", borderLeft: `3px solid ${section.color}` }}>
                  <div style={{ fontSize: "12px", fontWeight: 700, color: section.color, textTransform: "uppercase", letterSpacing: "0.5px", marginBottom: "4px" }}>{p.label}</div>
                  <div style={{ fontSize: "14px", color: "#ffffffcc", lineHeight: 1.5 }}>{p.text}</div>
                </div>
              ))}
            </div>
          </div>
        );

      case "tools":
        return (
          <div>
            <p style={{ fontSize: "14px", color: "#FF475799", lineHeight: 1.6, marginBottom: "20px", padding: "12px", background: "#FF475712", borderRadius: "8px", borderLeft: "3px solid #FF4757" }}>
              ⚠ {c.intro}
            </p>
            <div style={{ display: "flex", flexDirection: "column", gap: "12px" }}>
              {c.tools.map((t, i) => (
                <ToolCard key={i} tool={t} recommended={t.recommended} />
              ))}
            </div>
          </div>
        );

      case "comments":
        return (
          <div>
            <p style={{ fontSize: "14px", color: "#FFA50299", lineHeight: 1.6, marginBottom: "20px", padding: "12px", background: "#FFA50212", borderRadius: "8px", borderLeft: "3px solid #FFA502" }}>
              ⚡ {c.intro}
            </p>
            <div style={{ marginBottom: "28px" }}>
              <h3 style={{ fontSize: "14px", fontWeight: 700, color: "#ffffff88", textTransform: "uppercase", letterSpacing: "1px", marginBottom: "16px" }}>Воронка</h3>
              {c.funnel.map((s, i) => (
                <FunnelStep key={i} step={s} isLast={i === c.funnel.length - 1} />
              ))}
            </div>
            <h3 style={{ fontSize: "14px", fontWeight: 700, color: "#ffffff88", textTransform: "uppercase", letterSpacing: "1px", marginBottom: "12px" }}>Конверсии</h3>
            <div style={{ display: "flex", flexDirection: "column", gap: "8px" }}>
              {c.conversions.map((cv, i) => (
                <div key={i} style={{ display: "flex", justifyContent: "space-between", alignItems: "center", background: i === c.conversions.length - 1 ? "#7B68EE22" : "#ffffff06", padding: "12px 16px", borderRadius: "8px", border: i === c.conversions.length - 1 ? "1px solid #7B68EE44" : "none" }}>
                  <span style={{ fontSize: "13px", color: "#ffffffbb" }}>{cv.stage}</span>
                  <span style={{ fontSize: "15px", fontWeight: 800, color: i === c.conversions.length - 1 ? "#7B68EE" : "#fff" }}>{cv.rate}</span>
                </div>
              ))}
            </div>
          </div>
        );

      case "philippines":
      case "indonesia":
        return (
          <div>
            <CountryStats stats={c.stats} color={section.color} />

            <div style={{ marginBottom: "20px" }}>
              <h3 style={{ fontSize: "13px", fontWeight: 700, color: "#ffffff66", textTransform: "uppercase", letterSpacing: "1px", marginBottom: "10px" }}>🎯 Целевые группы</h3>
              {c.groups.map((g, i) => (
                <div key={i} style={{ padding: "8px 14px", background: "#ffffff06", borderRadius: "6px", fontSize: "13px", color: "#ffffffcc", marginBottom: "4px" }}>
                  {g}
                </div>
              ))}
            </div>

            <div style={{ marginBottom: "20px" }}>
              <h3 style={{ fontSize: "13px", fontWeight: 700, color: "#ffffff66", textTransform: "uppercase", letterSpacing: "1px", marginBottom: "8px" }}>🗣 Язык</h3>
              <p style={{ fontSize: "13px", color: "#ffffffbb", lineHeight: 1.6 }}>{c.language}</p>
            </div>

            <div style={{ marginBottom: "20px" }}>
              <h3 style={{ fontSize: "13px", fontWeight: 700, color: "#ffffff66", textTransform: "uppercase", letterSpacing: "1px", marginBottom: "8px" }}>⏰ Тайминг</h3>
              <p style={{ fontSize: "13px", color: "#ffffffbb", lineHeight: 1.6 }}>{c.timing}</p>
            </div>

            <div style={{ marginBottom: "20px" }}>
              <h3 style={{ fontSize: "13px", fontWeight: 700, color: "#ffffff66", textTransform: "uppercase", letterSpacing: "1px", marginBottom: "10px" }}>✅ Сигналы доверия</h3>
              {c.trustSignals.map((ts, i) => (
                <div key={i} style={{ display: "flex", alignItems: "flex-start", gap: "8px", marginBottom: "6px" }}>
                  <span style={{ color: "#2ED573", flexShrink: 0, marginTop: "1px" }}>✓</span>
                  <span style={{ fontSize: "13px", color: "#ffffffcc", lineHeight: 1.5 }}>{ts}</span>
                </div>
              ))}
            </div>

            {(c.scamWarning || c.legalWarning) && (
              <div style={{ background: "#FF475712", border: "1px solid #FF475733", borderRadius: "10px", padding: "14px", marginTop: "16px" }}>
                <div style={{ fontSize: "12px", fontWeight: 700, color: "#FF4757", marginBottom: "6px" }}>⚠ {section.id === "philippines" ? "СКАМ-ФАКТОР" : "ЮРИДИЧЕСКИЙ РИСК"}</div>
                <div style={{ fontSize: "13px", color: "#ffffffbb", lineHeight: 1.6 }}>{c.scamWarning || c.legalWarning}</div>
              </div>
            )}
          </div>
        );

      case "security":
        return (
          <div>
            <p style={{ fontSize: "14px", color: "#ffffffbb", lineHeight: 1.6, marginBottom: "20px" }}>{c.intro}</p>

            <h3 style={{ fontSize: "13px", fontWeight: 700, color: "#ffffff66", textTransform: "uppercase", letterSpacing: "1px", marginBottom: "12px" }}>🌐 Антидетект-браузеры</h3>
            <div style={{ display: "flex", flexDirection: "column", gap: "10px", marginBottom: "24px" }}>
              {c.browsers.map((b, i) => (
                <div key={i} style={{ background: b.recommended ? "#2ED57312" : "#ffffff06", border: b.recommended ? "1px solid #2ED57333" : "1px solid #ffffff08", borderRadius: "10px", padding: "14px", position: "relative" }}>
                  {b.recommended && <span style={{ position: "absolute", top: "8px", right: "8px", background: "#2ED573", color: "#000", fontSize: "10px", fontWeight: 700, padding: "2px 6px", borderRadius: "4px" }}>BEST VALUE</span>}
                  <div style={{ display: "flex", justifyContent: "space-between", alignItems: "baseline", marginBottom: "4px" }}>
                    <span style={{ fontWeight: 700, color: "#fff", fontSize: "15px" }}>{b.name}</span>
                    <span style={{ fontWeight: 800, color: "#2ED573", fontSize: "14px" }}>{b.price}</span>
                  </div>
                  <div style={{ fontSize: "12px", color: "#ffffff55", marginBottom: "4px" }}>{b.profiles} профилей</div>
                  <div style={{ fontSize: "13px", color: "#ffffffaa" }}>{b.note}</div>
                </div>
              ))}
            </div>

            <h3 style={{ fontSize: "13px", fontWeight: 700, color: "#ffffff66", textTransform: "uppercase", letterSpacing: "1px", marginBottom: "12px" }}>🔗 Резидентные прокси</h3>
            <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "10px", marginBottom: "24px" }}>
              {c.proxies.map((p, i) => (
                <div key={i} style={{ background: "#ffffff06", borderRadius: "8px", padding: "12px" }}>
                  <div style={{ fontWeight: 700, color: "#fff", fontSize: "14px" }}>{p.name}</div>
                  <div style={{ fontWeight: 800, color: "#2ED573", fontSize: "15px", margin: "4px 0" }}>{p.price}</div>
                  <div style={{ fontSize: "12px", color: "#ffffff77" }}>{p.note}</div>
                </div>
              ))}
            </div>

            <h3 style={{ fontSize: "13px", fontWeight: 700, color: "#ffffff66", textTransform: "uppercase", letterSpacing: "1px", marginBottom: "12px" }}>🔥 Прогрев аккаунтов</h3>
            <div style={{ display: "flex", flexDirection: "column", gap: "8px", marginBottom: "24px" }}>
              {c.warming.map((w, i) => (
                <div key={i} style={{ display: "flex", gap: "12px", alignItems: "flex-start" }}>
                  <div style={{ background: "#2ED57322", color: "#2ED573", borderRadius: "6px", padding: "4px 10px", fontSize: "11px", fontWeight: 700, whiteSpace: "nowrap", minWidth: "80px", textAlign: "center" }}>{w.week}</div>
                  <div style={{ fontSize: "13px", color: "#ffffffbb", lineHeight: 1.5 }}>{w.actions}</div>
                </div>
              ))}
            </div>

            <h3 style={{ fontSize: "13px", fontWeight: 700, color: "#ffffff66", textTransform: "uppercase", letterSpacing: "1px", marginBottom: "10px" }}>📝 Правила контента</h3>
            {c.contentRules.map((r, i) => (
              <div key={i} style={{ display: "flex", gap: "8px", marginBottom: "6px", alignItems: "flex-start" }}>
                <span style={{ color: section.color, flexShrink: 0 }}>→</span>
                <span style={{ fontSize: "13px", color: "#ffffffbb" }}>{r}</span>
              </div>
            ))}
          </div>
        );

      case "budget":
        return (
          <div>
            <h3 style={{ fontSize: "13px", fontWeight: 700, color: "#ffffff66", textTransform: "uppercase", letterSpacing: "1px", marginBottom: "12px" }}>Рекомендуемый стек</h3>
            <div style={{ display: "flex", flexDirection: "column", gap: "6px", marginBottom: "28px" }}>
              {c.stack.map((s, i) => (
                <div key={i} style={{ display: "flex", justifyContent: "space-between", alignItems: "center", background: "#ffffff06", borderRadius: "8px", padding: "12px 14px" }}>
                  <div>
                    <div style={{ fontSize: "13px", color: "#ffffffbb" }}>{s.component}</div>
                    <div style={{ fontSize: "11px", color: "#5352ED", fontWeight: 600 }}>{s.tool}</div>
                  </div>
                  <div style={{ fontSize: "14px", fontWeight: 800, color: "#fff", whiteSpace: "nowrap" }}>{s.cost}</div>
                </div>
              ))}
            </div>

            <h3 style={{ fontSize: "13px", fontWeight: 700, color: "#ffffff66", textTransform: "uppercase", letterSpacing: "1px", marginBottom: "12px" }}>Масштабы операции</h3>
            <div style={{ display: "flex", flexDirection: "column", gap: "12px", marginBottom: "24px" }}>
              {c.scales.map((s, i) => (
                <div key={i} style={{ background: i === 1 ? "#5352ED18" : "#ffffff06", border: i === 1 ? "1px solid #5352ED44" : "1px solid #ffffff08", borderRadius: "12px", padding: "16px", position: "relative" }}>
                  {i === 1 && <span style={{ position: "absolute", top: "10px", right: "10px", background: "#5352ED", color: "#fff", fontSize: "10px", fontWeight: 700, padding: "2px 8px", borderRadius: "4px" }}>РЕКОМЕНДУЮ</span>}
                  <div style={{ fontSize: "16px", fontWeight: 800, color: "#fff", marginBottom: "10px" }}>{s.scale}</div>
                  <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "8px" }}>
                    <div><span style={{ fontSize: "11px", color: "#ffffff55" }}>Группы</span><br/><span style={{ fontSize: "14px", fontWeight: 700, color: "#ffffffcc" }}>{s.groups}</span></div>
                    <div><span style={{ fontSize: "11px", color: "#ffffff55" }}>Аккаунты</span><br/><span style={{ fontSize: "14px", fontWeight: 700, color: "#ffffffcc" }}>{s.accounts}</span></div>
                    <div><span style={{ fontSize: "11px", color: "#ffffff55" }}>Бюджет</span><br/><span style={{ fontSize: "16px", fontWeight: 800, color: "#5352ED" }}>{s.budget}</span></div>
                    <div><span style={{ fontSize: "11px", color: "#ffffff55" }}>Лиды</span><br/><span style={{ fontSize: "14px", fontWeight: 700, color: "#2ED573" }}>{s.leads}</span></div>
                  </div>
                </div>
              ))}
            </div>

            <h3 style={{ fontSize: "13px", fontWeight: 700, color: "#ffffff66", textTransform: "uppercase", letterSpacing: "1px", marginBottom: "10px" }}>Заметки</h3>
            {c.notes.map((n, i) => (
              <div key={i} style={{ fontSize: "13px", color: "#ffffffaa", marginBottom: "4px" }}>• {n}</div>
            ))}
          </div>
        );

      case "roadmap":
        return (
          <div style={{ display: "flex", flexDirection: "column", gap: "20px" }}>
            {c.phases.map((p, i) => (
              <div key={i} style={{ background: "#ffffff06", borderRadius: "12px", padding: "18px", borderLeft: `3px solid ${section.color}` }}>
                <div style={{ display: "flex", justifyContent: "space-between", alignItems: "baseline", marginBottom: "4px" }}>
                  <span style={{ fontSize: "12px", fontWeight: 700, color: section.color }}>{p.phase}</span>
                  <span style={{ fontSize: "11px", color: "#ffffff55" }}>{p.period}</span>
                </div>
                <div style={{ fontSize: "16px", fontWeight: 800, color: "#fff", marginBottom: "12px" }}>{p.title}</div>
                {p.tasks.map((t, j) => (
                  <div key={j} style={{ display: "flex", gap: "8px", marginBottom: "6px", alignItems: "flex-start" }}>
                    <span style={{ color: "#ffffff33", flexShrink: 0, fontSize: "12px", marginTop: "1px" }}>☐</span>
                    <span style={{ fontSize: "13px", color: "#ffffffbb", lineHeight: 1.5 }}>{t}</span>
                  </div>
                ))}
              </div>
            ))}
          </div>
        );

      default:
        return null;
    }
  };

  return (
    <div style={{ background: "#0a0a12", minHeight: "100vh", color: "#fff", fontFamily: "'Segoe UI', -apple-system, sans-serif" }}>
      {/* Header */}
      <div style={{ background: "linear-gradient(135deg, #0a0a1a, #141428)", borderBottom: "1px solid #ffffff10", padding: "20px 20px 16px" }}>
        <div style={{ fontSize: "11px", color: "#FF6B35", fontWeight: 700, textTransform: "uppercase", letterSpacing: "2px", marginBottom: "6px" }}>
          Apex Talent / HuntMe
        </div>
        <h1 style={{ fontSize: "22px", fontWeight: 800, color: "#fff", lineHeight: 1.2, marginBottom: "8px" }}>
          Автоматизация FB-рекрутинга
        </h1>
        <p style={{ fontSize: "13px", color: "#ffffff66", lineHeight: 1.5 }}>
          Филиппины + Индонезия • Постинг + ответы + воронка в Telegram
        </p>
      </div>

      {/* Navigation */}
      <div style={{ display: "flex", overflowX: "auto", gap: "6px", padding: "12px 16px", borderBottom: "1px solid #ffffff08", WebkitOverflowScrolling: "touch" }}>
        {sections.map((s) => (
          <button
            key={s.id}
            onClick={() => { setActiveSection(s.id); setShowRisks(false); }}
            style={{
              background: activeSection === s.id ? s.color + "22" : "transparent",
              border: activeSection === s.id ? `1px solid ${s.color}55` : "1px solid #ffffff10",
              borderRadius: "8px",
              padding: "8px 14px",
              color: activeSection === s.id ? s.color : "#ffffff77",
              fontSize: "12px",
              fontWeight: 600,
              cursor: "pointer",
              whiteSpace: "nowrap",
              transition: "all 0.2s ease",
              flexShrink: 0,
            }}
          >
            {s.icon} {s.title}
          </button>
        ))}
        <button
          onClick={() => { setShowRisks(true); setActiveSection(""); }}
          style={{
            background: showRisks ? "#FF475722" : "transparent",
            border: showRisks ? "1px solid #FF475755" : "1px solid #ffffff10",
            borderRadius: "8px",
            padding: "8px 14px",
            color: showRisks ? "#FF4757" : "#ffffff77",
            fontSize: "12px",
            fontWeight: 600,
            cursor: "pointer",
            whiteSpace: "nowrap",
            flexShrink: 0,
          }}
        >
          ⚡ Матрица рисков
        </button>
      </div>

      {/* Content */}
      <div style={{ padding: "20px 16px 40px" }}>
        {showRisks ? (
          <div>
            <h2 style={{ fontSize: "18px", fontWeight: 800, color: "#FF4757", marginBottom: "16px" }}>⚡ Матрица рисков</h2>
            <div style={{ display: "flex", flexDirection: "column", gap: "12px" }}>
              {riskMatrix.map((r, i) => (
                <div key={i} style={{ background: "#ffffff06", borderRadius: "12px", padding: "16px", borderLeft: "3px solid #FF475744" }}>
                  <div style={{ fontSize: "15px", fontWeight: 700, color: "#fff", marginBottom: "8px" }}>{r.risk}</div>
                  <div style={{ display: "flex", gap: "10px", marginBottom: "10px" }}>
                    <div style={{ fontSize: "11px", color: "#ffffff55" }}>Вероятность: <RiskBadge level={r.probability} /></div>
                    <div style={{ fontSize: "11px", color: "#ffffff55" }}>Импакт: <RiskBadge level={r.impact} /></div>
                  </div>
                  <div style={{ fontSize: "13px", color: "#2ED573cc", background: "#2ED57310", borderRadius: "6px", padding: "10px 12px", lineHeight: 1.5 }}>
                    🛡 {r.mitigation}
                  </div>
                </div>
              ))}
            </div>
          </div>
        ) : (
          <div>
            <h2 style={{ fontSize: "18px", fontWeight: 800, color: section?.color, marginBottom: "16px" }}>
              {section?.icon} {section?.title}
            </h2>
            {renderContent()}
          </div>
        )}
      </div>
    </div>
  );
}
