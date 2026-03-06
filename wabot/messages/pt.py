"""PT-BR messages for Gabi WA bot funnel.

Based on: knowledge/marketing/wa-bot-funnel.md (RU version for approval)
Translated and adapted for Brazilian Portuguese market.

Structure:
  STEPS dict: step_number → list of messages to send in sequence.
  "+" continues to next step, "1"/"2" for branching.
  Free text → AI (Groq).
"""

# Gabi's photo URL (AI-generated Brazilian girl)
GABI_PHOTO_URL = "https://apextalent.pro/assets/gabi.jpg"

# Step messages: each value is a list of strings sent sequentially
STEPS: dict[int, list[str]] = {
    # STEP 0 — triggered on first message from lead
    0: [
        # Capybara meme image sent before text (handled in fsm.py)
        "👆 Esse meme da capivara não é brincadeira, é exatamente o que acontece aqui ✌️",
    ],

    # STEP 1 — intro / who is Gabi
    1: [
        "✌️ Oi! Me chamo Gabi, tenho 26 anos e fico muito feliz que você se interessou pelo meu projeto e está lendo essa mensagem",
        "Isso significa que você, assim como eu e as outras meninas do nosso projeto, quer aproveitar a vida ao máximo...",
        "...e eu ADORO pessoas assim, porque é exatamente assim que se deve viver! 💗",
        "Vou te contar um pouco sobre mim e depois você me conta sobre você, tá?",
        "Manda um *+* pra continuar 👇",
    ],

    # STEP 2 — Gabi's story (ordinary world)
    2: [
        "Há dois anos atrás eu estava vendendo no shopping do interior de SP, ganhando R$1.800 por mês 😅",
        "Trabalhava 6 dias por semana, ficava em pé 8 horas, e no fim do mês não sobrava nada pra ajudar minha mãe...",
        "Honestamente? Eu estava começando a me sentir presa. Sabe aquela sensação?",
        "Manda *+* pra continuar 👇",
    ],

    # STEP 3 — turning point
    3: [
        "Aí uma amiga me falou sobre um projeto de entretenimento digital que ela estava fazendo...",
        "Fiquei desconfiada no começo — achei que era golpe ou coisa assim 😂",
        "Mas ela me mostrou os comprovantes. R$4.200 no primeiro mês. Fiquei de queixo caído.",
        "Decidi tentar. E mudou TUDO.",
        "Manda *+* pra ouvir o que aconteceu 👇",
    ],

    # STEP 4 — transformation
    4: [
        "No primeiro mês recebi R$3.100. Paguei as dívidas da minha mãe.",
        "No terceiro mês já estava em R$5.800. Comecei a guardar.",
        "No sexto mês? Fui para Dubai. Pela primeira vez na vida, viajei de avião. 🛫",
        "Hoje ganho R$12K+ por mês. Trabalho em casa, no meu horário. E ajudo outras meninas a fazerem o mesmo.",
        "Por isso criei o *Projeto Centelha* ✨",
        "Manda *+* pra saber como funciona 👇",
    ],

    # STEP 5 — what is the project
    5: [
        "O Projeto Centelha conecta meninas brasileiras a plataformas internacionais de *streaming de entretenimento*.",
        "É legal, é seguro, e é 100% online — você trabalha de casa, no seu ritmo.",
        "Sem aparecer fisicamente em lugar nenhum. Sem exigência de experiência.",
        "O que importa é sua personalidade e sua energia ✨",
        "Curiosa pra saber mais? Manda *+* 👇",
    ],

    # STEP 6 — social proof / cases
    6: [
        "Deixa eu te mostrar umas meninas que estão no projeto:",
        "🌟 *Camila, 23 anos, Recife* — era garçonete, R$1.400/mês. Hoje: R$8.900/mês. 4 meses no projeto.",
        "🌟 *Juliana, 28 anos, BH* — estava desempregada. Hoje: R$6.200/mês. Viajou pra Europa pela primeira vez.",
        "Resultados variam, claro — mas esses são reais 💯",
        "Manda *+* pra eu te contar como funciona na prática 👇",
    ],

    # STEP 7 — how it works (practical)
    7: [
        "Na prática: você se conecta a uma plataforma de streaming, cria seu perfil e interage com o público.",
        "É tipo um show ao vivo — você conversa, ri, conta histórias. Sua personalidade é o produto.",
        "Sem nudez. Sem conteúdo adulto. É entretenimento mesmo — como TikTok Live, mas pago.",
        "Os viewers pagam para assistir e interagir com você 💰",
        "Manda *+* pra ver quanto dá pra ganhar 👇",
    ],

    # STEP 8 — earnings breakdown
    8: [
        "Os ganhos são em dólar, pagos semanalmente direto pra sua conta. 💵",
        "A média das meninas no primeiro mês: $300–$600 USD (R$1.800–R$3.600).",
        "Quem se dedica mais, chega a $1.000–$2.000 USD por mês dentro de 3 meses.",
        "Não é salário fixo — é baseado em audiência e consistência. Quanto mais você aparece, mais ganha.",
        "Manda *+* pra continuar 👇",
    ],

    # STEP 9 — objection handling (schedule)
    9: [
        "Você decide seus próprios horários — não tem chefe te dizendo quando trabalhar.",
        "A maioria das meninas trabalha 3–5 horas por dia. Algumas fazem mais, algumas menos.",
        "Dá pra conciliar com faculdade, outro emprego, família.",
        "Manda *+* 👇",
    ],

    # STEP 10 — what's needed
    10: [
        "Pra começar você precisa de:",
        "📱 Smartphone com câmera boa (Android ou iPhone)\n🌐 Internet estável\n😊 Disposição pra aparecer e interagir",
        "Só isso! A gente te ensina todo o resto.",
        "Manda *+* 👇",
    ],

    # STEP 11 — qualification Q1 (device check)
    11: [
        "Me conta: você tem smartphone Android ou iPhone? 📱",
        "Manda *1* pra Android ou *2* pra iPhone:",
    ],

    # STEP 12 — qualification Q2 (city/location)
    12: [
        "Perfeito! E de qual cidade você é? 🗺️",
        "(Pode falar o estado também, tudo bem)",
    ],

    # STEP 13 — qualification Q3 (availability)
    13: [
        "Boa! E você tem pelo menos 3 horas livres por dia pra começar?",
        "Manda *1* pra Sim ou *2* pra Não tenho certeza:",
    ],

    # STEP 14 — post qualification
    14: [
        "Perfeito! Você parece ser exatamente o perfil que a gente procura! 🌟",
        "Agora vou te passar pra próxima etapa: uma conversa rápida com nossa equipe.",
        "É só pra a gente se conhecer melhor e ver como podemos te ajudar a começar.",
        "Manda *+* pra saber como funciona essa conversa 👇",
    ],

    # STEP 15 — interview intro
    15: [
        "A gente faz uma videochamada rápida — uns 20-30 minutos.",
        "Não é entrevista de emprego formal, é uma conversa mesmo. Casual, sem pressão.",
        "Nossa equipe te explica tudo em detalhes e tira todas as suas dúvidas.",
        "Quer marcar? Manda *+* 👇",
    ],

    # STEP 16 — booking
    16: [
        "Ótimo! Vou te conectar com nossa equipe agora para agendar sua conversa. 📅",
        "Aguarda um momento...",
    ],
}

# Follow-up messages (sent when lead goes silent)
FOLLOWUP = {
    1: "Oi! Tudo bem? Vi que você parou por aqui... tem alguma dúvida que posso te ajudar? 😊",
    2: "Oi de novo! 👋 Sei que a vida é corrida... mas não queria que você perdesse essa oportunidade. Quer continuar de onde parou?",
    3: "Última mensagem, prometo! 😅 Se mudar de ideia, é só me chamar. O projeto continua aberto pra você 💗",
}

# Capybara meme image URL (step 0)
CAPYBARA_MEME_URL = "https://apextalent.pro/assets/capybara-money.jpg"
