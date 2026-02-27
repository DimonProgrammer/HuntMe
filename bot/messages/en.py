"""English messages — all user-facing text for the bot."""

# ═══ MENU ═══

MAIN_MENU_TEXT = (
    "Hey! Welcome to Apex Talent 👋\n\n"
    "We hire Live Stream Operators — a behind-the-scenes remote role. "
    "You help streamers with OBS, chat, and scheduling. Never on camera.\n\n"
    "💰 $600-800/month starting, paid in USD\n"
    "📈 Top performers earn $1,500+/month\n"
    "🏠 100% remote, flexible shifts\n"
    "🎓 Paid training — no experience needed\n"
    "🛡 Zero fees — we pay you, never the other way\n\n"
    "Takes 2-3 minutes to apply. Ready?"
)

BTN_APPLY = "🚀 Apply Now"
BTN_VACANCY = "💼 About the Vacancy"
BTN_COMPANY = "🏢 About the Company"
BTN_QUESTION = "❓ Ask a Question"
BTN_BACK_MENU = "⬅️ Back to Menu"
BTN_BACK = "⬅️ Back"
BTN_CONTINUE = "▶️ Continue filling"
BTN_REAPPLY = "🔄 Start new application"
BTN_ASK_ANOTHER = "❓ Ask another question"

# Status labels (for duplicate check)
STATUS_LABELS = {
    "new": "under review",
    "screened": "screened, waiting for decision",
    "interview_invited": "interview scheduled",
    "active": "active operator",
    "declined": "declined",
    "churned": "inactive",
}

DUPLICATE_CHECK = (
    "Hey {name}! 👋\n\n"
    "You've already applied. Your current status: {status}.\n\n"
    "Would you like to start a new application?"
)

ASK_QUESTION_PROMPT = "Type your message and our team will get back to you shortly. 💬"
ASK_QUESTION_PROMPT_RESUME = (
    "Type your question and our team will get back to you shortly. 💬\n\n"
    "When you're done, tap 'Continue filling' to resume your application."
)
QUESTION_SENT = (
    "Thanks for your question! 🙂\n\n"
    "Our team will get back to you shortly. "
    "You'll receive a reply right here in this chat."
)
QUESTION_SENT_RESUME = (
    "Thanks! Our team will reply shortly. 🙂\n\n"
    "Tap 'Continue filling' to resume your application."
)
MSG_SENT = "Message sent! Our team will reply shortly. 💬"
RESUME_TEXT = "Great, let's continue! 🙂"
RESUME_FALLBACK = "Let's continue from where you left off!"

REFERRAL_TEXT = (
    "Your personal referral link:\n\n"
    "{link}\n\n"
    "Share it with friends! When someone you refer gets hired, "
    "you earn $50-100 per person.\n\n"
    "The more people you refer, the more you earn:\n"
    "  1-3 hires: $50 each\n"
    "  4-6 hires: $75 each\n"
    "  7+ hires: $100 each"
)

ERROR_GENERIC = "Sorry, something went wrong. Please try again."

# ═══ VACANCY INFO ═══

VACANCY_TEXT = (
    "LIVE STREAM OPERATOR\n\n"
    "What you'll do:\n"
    "  • Set up streaming software (OBS) and manage stream tech\n"
    "  • Moderate live chats during broadcasts\n"
    "  • Schedule and organize streaming sessions\n"
    "  • Provide technical support to content creators\n"
    "  • You NEVER appear on camera — fully behind the scenes\n\n"
    "Compensation:\n"
    "  • Starting: $600-800/month\n"
    "  • After 1-2 months: $1,000-1,200/month\n"
    "  • Top performers: $1,500+/month\n"
    "  • Paid training: 5-7 days, $30 per shift\n"
    "  • All payments in USD\n\n"
    "Schedule:\n"
    "  • 5 days/week, 2 days off\n"
    "  • 6-8 hours/day\n"
    "  • 4 shift options: morning / day / evening / night\n"
    "  • Payment every Monday in USD\n\n"
    "Requirements:\n"
    "  • Windows PC or laptop (MacBooks not supported)\n"
    "  • CPU: Intel Core i3 10th gen+ or AMD Ryzen 3 3000+\n"
    "  • GPU: NVIDIA GTX 1060 6GB+ or AMD RX 5500+\n"
    "  • Internet: 100 Mbps+\n"
    "  • English: B1 (Intermediate) minimum\n"
    "  • Age: 18+"
)

COMPANY_TEXT = (
    "ABOUT APEX TALENT\n\n"
    "We're an international talent management agency that works "
    "with content creators on streaming platforms.\n\n"
    "What we do:\n"
    "  • Connect talented people with streaming opportunities worldwide\n"
    "  • Provide full training and ongoing support for every team member\n"
    "  • Handle the technical side so creators can focus on content\n\n"
    "Our team:\n"
    "  • Operating in 15+ countries\n"
    "  • 100% remote — work from anywhere\n"
    "  • Payment every Monday in USD, without exception\n"
    "  • Dedicated mentor for every new team member\n\n"
    "We never ask for upfront payments.\n"
    "Your first earnings start during paid training ($30/shift, 5-7 days)."
)

# ═══ OPERATOR FLOW — STEP PROMPTS ═══

STEP_NAME = "What is your full name?"
STEP_NAME_GREETING = "Nice to meet you, {name}! 🙂"
STEP_NAME_VALIDATION = "Please enter your full name (e.g., John Smith)."

STEP_PC = "Do you have a Windows PC or laptop?"
BTN_PC_DESKTOP = "🖥️ Yes, PC/Desktop"
BTN_PC_LAPTOP = "💻 Yes, Laptop"
BTN_PC_NO = "❌ No"
PC_GREAT = "Great! 👍"

STEP_NO_PC = (
    "I see. This role requires a Windows PC or laptop for the streaming software.\n\n"
    "Are you planning to get one in the near future?"
)
BTN_NOPC_SOON = "✅ Yes, within 1-2 weeks"
BTN_NOPC_NO = "🤷 No plans yet"
NO_PC_CONTINUE = "Got it, no worries! Let's continue — we'll figure out the PC situation later."
STEP_NO_PC_QUESTION = "Are you planning to get a Windows PC in the near future?"

STEP_AGE = "How old are you?"
STEP_AGE_VALIDATION = "Please enter your age as a number (e.g., 22)."

STEP_STUDY = "Are you currently studying or working?"
BTN_WORKING = "💼 Working"
BTN_STUDENT_ONLINE = "🎓 Student (online classes)"
BTN_STUDENT_CAMPUS = "🏫 Student (on campus)"
BTN_NEITHER = "🏠 Neither"

STEP_ENGLISH = (
    "How well do you speak English?\n\n"
    "We need at least conversational level — you'll be moderating English chats.\n\n"
    "You can also rate yourself from 1 to 10."
)
BTN_ENG_BASIC = "📗 Basic"
BTN_ENG_B1 = "📘 Can hold a conversation"
BTN_ENG_B2 = "📙 Comfortable"
BTN_ENG_C1 = "📕 Fluent"
BTN_ENG_NATIVE = "🌟 Native speaker"
ENGLISH_VALIDATION = "Please use the buttons above or rate yourself 1-10. 👆"

SOCIAL_PROOF = (
    "You're doing great! Almost halfway there.\n\n"
    "People like you are already earning with us:\n"
    "  Alex from Europe — $250/week after 2 months\n"
    "  Daniel from Asia — started from zero, now $200/week\n\n"
    "Just a few more questions about your setup!"
)

STEP_PC_CONFIDENCE = (
    "How comfortable are you with Windows?\n\n"
    "For example: installing programs, troubleshooting, changing settings?\n\n"
    "You can rate yourself from 1 to 10."
)

STEP_CPU = (
    "What is your processor (CPU)?\n\n"
    "How to check:\n"
    "Settings > System > About > look for 'Processor'\n\n"
    "Example: Intel Core i5-12400 or AMD Ryzen 5 5600\n\n"
    "Not sure? Tap the button — we'll ask a few simple questions instead."
)
BTN_NOT_SURE = "🤔 Not sure"
BTN_SKIP = "🤔 I'm not sure / skip"

STEP_CPU_AGE = "How old is your computer?"
STEP_CPU_AGE_INTRO = "No worries! A few quick questions instead."
BTN_PC_NEW = "🆕 Less than 2 years"
BTN_PC_MID = "📅 2-4 years"
BTN_PC_OLD = "📆 5+ years"

STEP_CPU_USAGE = "What do you mainly use your computer for?"
BTN_GAMING = "🎮 Gaming"
BTN_WORK = "💼 Work / Office"
BTN_BROWSING = "🌐 Browsing / Social media"
BTN_CREATIVE = "🎨 Video editing / Design"

STEP_GPU = (
    "What is your graphics card (GPU)?\n\n"
    "How to check:\n"
    "Settings > System > Display > Advanced display > look for GPU info\n\n"
    "Example: NVIDIA GeForce RTX 3060 or AMD Radeon RX 6600\n\n"
    "Not sure? Tap the button below."
)

STEP_GPU_GAMING = "Can your computer run video games?"
STEP_GPU_GAMING_INTRO = "One more quick question."
BTN_GAME_MODERN = "🎮 Yes, modern games (GTA, Fortnite)"
BTN_GAME_BASIC = "🕹️ Yes, but only simple/old games"
BTN_GAME_NO = "❌ No / Never tried"

STEP_INTERNET = (
    "What is your internet speed?\n\n"
    "You can check at speedtest.net\n\n"
    "Also — are you on WiFi or plugged in with a cable?"
)
STEP_INTERNET_ALT = (
    "What is your internet speed? (minimum 100 Mbps required)\n\n"
    "You can check at speedtest.net\n\n"
    "Also — do you have a LAN (ethernet) connection or Wi-Fi only?"
)

STEP_START_DATE = (
    "When would you be ready to start?\n\n"
    "We can schedule your interview and start training the same day!"
)

STEP_CONTACT = (
    "Last one!\n\n"
    "Please share your contact for the interview:\n"
    "• Telegram @username (preferred)\n• Or WhatsApp number"
)
STEP_CONTACT_LAST = (
    "Last question! 🙂\n\n"
    "Please share your contact for the interview:\n"
    "• Telegram @username (preferred)\n"
    "• Or WhatsApp number"
)
CONTACT_VALIDATION = (
    "Please type your contact info:\n"
    "• Telegram @username (preferred)\n"
    "• Or WhatsApp number"
)

# ═══ SCREENING / COMPLETION ═══

APPLICATION_COMPLETE = (
    "Thank you for completing the application! 🎉\n\n"
    "I'm reviewing your information now..."
)
APPLICATION_FALLBACK = (
    "Thank you for applying! 🎉\n\n"
    "Our team will review your application and get back to you "
    "within 24 hours to schedule your interview.\n\n"
    "Talk to you soon!"
)

# ═══ PHOTO HANDLING ═══

PHOTO_READING = "📸 Reading your screenshot..."
PHOTO_CPU_FAIL = (
    "Sorry, I couldn't read that. Could you type your CPU model instead?\n\n"
    "Example: Intel Core i5-12400 or AMD Ryzen 5 5600X"
)
PHOTO_GPU_FAIL = (
    "Sorry, I couldn't read that. Could you type your GPU model instead?\n\n"
    "Example: NVIDIA GeForce GTX 1650 or AMD Radeon RX 580"
)
PHOTO_SPEED_FAIL = (
    "Sorry, I couldn't read that screenshot.\n"
    "Could you type your internet speed instead?\n\n"
    "For example: Download 150 Mbps, Upload 50 Mbps, Wi-Fi"
)
PHOTO_EXTRACTED = "Got it: {value}"
CPU_INPUT_PROMPT = "Please type your CPU model or send a screenshot from Task Manager / System Info."
GPU_INPUT_PROMPT = "Please type your GPU model or send a screenshot."
SPEED_INPUT_PROMPT = "Please type your internet speed or send a screenshot of your speed test."
START_DATE_PROMPT = "Please type when you'd be ready to start."

# ═══ MISC FLOW ═══

USE_BUTTONS = "Please use the buttons above to answer. 👆"
QUESTION_FORWARDED = (
    "Great question! I've forwarded it to our team — "
    "they'll get back to you shortly. 🙂\n\n"
    "In the meantime, let's continue with the application."
)

# ═══ REMINDER ═══

REMINDER_SET = "Got it! I'll remind you in {label}. See you soon! 👋"
REMINDER_LABELS = {30: "30 minutes", 60: "1 hour", 180: "3 hours", 720: "12 hours"}

REMINDER_LATE_STEP = (
    "Hey! You're almost done — just a couple more steps! 🏁\n\n"
    "If now's not a good time, pick when you'd like a reminder:"
)
REMINDER_EARLY_STEP = (
    "Hey! 👋 No rush — if now's not a good time, pick when you'd like a reminder:"
)
REMINDER_FALLBACK = "Hey! Just checking in — ready to continue? 🙂"

# ═══ FOLLOWUP TEMPLATES ═══

WARM_GREETING = (
    "Hi {name}! 👋\n\n"
    "Thanks for reaching out! I'm glad you're interested in the position.\n\n"
    "We're a talent management agency that works with content creators "
    "on streaming platforms. We're looking for Live Stream Operators "
    "to join our remote team.\n\n"
    "Here's a quick overview:\n\n"
    "💰 Starting pay: $600-800/month in USD\n"
    "📈 Growth: $1,000-1,500+/month within 1-2 months\n"
    "🏠 100% remote — work from home\n"
    "📅 Schedule: 5/2, 6-8 hours/day, you choose your shift\n"
    "🎓 Paid training: 5-7 days with a personal mentor ($30/shift)\n"
    "💵 Payment every Monday in USD\n\n"
    "Your role: technical setup (OBS), chat moderation, "
    "scheduling — all behind the scenes. You never appear on camera.\n\n"
    "Let me ask you a few quick questions to see if this is a good fit. "
    "It'll take about 2 minutes! 🙂\n\n"
    "What is your full name?"
)

# Landing lead version — name already known, skip the name question
WARM_GREETING_LANDING = (
    "Hi {name}! 👋\n\n"
    "Thanks for reaching out! I'm glad you're interested in the position.\n\n"
    "We're a talent management agency that works with content creators "
    "on streaming platforms. We're looking for Live Stream Operators "
    "to join our remote team.\n\n"
    "Here's a quick overview:\n\n"
    "💰 Starting pay: $600-800/month in USD\n"
    "📈 Growth: $1,000-1,500+/month within 1-2 months\n"
    "🏠 100% remote — work from home\n"
    "📅 Schedule: 5/2, 6-8 hours/day, you choose your shift\n"
    "🎓 Paid training: 5-7 days with a personal mentor ($30/shift)\n"
    "💵 Payment every Monday in USD\n\n"
    "Your role: technical setup (OBS), chat moderation, "
    "scheduling — all behind the scenes. You never appear on camera.\n\n"
    "Let me ask you a few quick questions to see if this is a good fit. "
    "It'll take about 2 minutes! 🙂"
)

DECLINE_NO_PC = (
    "Thank you for your interest! 🙏\n\n"
    "This role needs a Windows PC or laptop for the streaming software. "
    "Many of our operators started by getting a refurbished one for $150-200 — "
    "it's a solid investment that pays for itself in the first week.\n\n"
    "We'll keep your application on file — just send /start when you're ready "
    "and we'll pick up where you left off!\n\n"
    "💡 Know someone with a PC who might be interested? "
    "Share this link: t.me/apextalent_bot — you could both benefit! 🙂"
)

DECLINE_UNDERAGE = (
    "Thank you for your interest! 🙏\n\n"
    "You need to be 18+ for this role — it's a platform requirement. "
    "But don't worry, we'll be here when you turn 18! Just send /start again "
    "and we'll get you going.\n\n"
    "💡 In the meantime, know anyone 18+ who's looking for remote work? "
    "Share this link: t.me/apextalent_bot — they'll thank you! 🙂\n\n"
    "Best of luck with your studies! 📚"
)

DECLINE_STUDENT_INPERSON = (
    "Thank you for your interest! 🙏\n\n"
    "The shifts (6-8 hours, 5 days/week) are tough to combine with "
    "in-person classes. But if your schedule changes — maybe during "
    "a semester break or if you switch to online classes — just send /start "
    "and we'll reopen your application.\n\n"
    "💡 Know any friends studying online or already graduated? "
    "Share this link: t.me/apextalent_bot — $600-800/month remote work! 🙂\n\n"
    "Good luck with your studies! 📚"
)

DECLINE_HARDWARE = (
    "Thank you for completing the application! 🙏\n\n"
    "Your hardware is close, but the streaming software needs a bit more power. "
    "Here's what you'd need:\n\n"
    "• CPU: Intel Core i3 10th gen+ or AMD Ryzen 3 3000+\n"
    "• GPU: NVIDIA GTX 1060 6GB+ or AMD RX 5500+\n"
    "• Internet: 100 Mbps+\n\n"
    "A small upgrade could get you there! If you upgrade in the future, "
    "just send /start — we'll have your info on file.\n\n"
    "💡 Know someone with a gaming PC? "
    "Share this link: t.me/apextalent_bot — $600-800/month remote work! 🙂"
)

DECLINE_ENGLISH = (
    "Thank you for your interest! 🙏\n\n"
    "This role involves moderating English-language chats, so we need "
    "at least a conversational level. But English improves fast with practice!\n\n"
    "Try free apps like Duolingo or watching English YouTube for 2-3 months, "
    "then send /start again — we'd love to reconsider you.\n\n"
    "💡 Know someone who speaks English well and wants remote work? "
    "Share this link: t.me/apextalent_bot — $600-800/month remote work! 🙂"
)

DECLINE_GENERIC = (
    "Thank you for your interest! 🙏\n\n"
    "We can't move forward with your application right now, "
    "but we'll keep your info for future openings.\n\n"
    "💡 Know someone looking for remote work ($600-800/month)? "
    "Share this link: t.me/apextalent_bot 🙂\n\n"
    "Wishing you all the best!"
)

FOLLOWUP_NO_RESPONSE_INITIAL = (
    "Hey! 👋\n\n"
    "Just wanted to follow up — did you get a chance to look at the details "
    "I sent about the Live Stream Operator position?\n\n"
    "We still have a few interview slots available this week. "
    "Let me know if you're interested and I'll get you set up! 😊"
)

FOLLOWUP_NO_RESPONSE = (
    "Hi again! 🙂\n\n"
    "I know you're probably busy — just a quick reminder that "
    "we're looking for operators to start next week.\n\n"
    "Starting pay is $600-800/month in USD, fully remote, and we provide all the training.\n\n"
    "If you're interested, just reply with \"Yes\" and I'll send you the next steps. "
    "If not, no worries at all! 🙏"
)

FOLLOWUP_THINKING = (
    "Hey! Just checking in 😊\n\n"
    "Have you had a chance to think about the operator position?\n\n"
    "I reserved an interview slot for you — it's a quick 15-min Zoom call "
    "where we explain everything in detail and answer all your questions.\n\n"
    "Would you like to keep the slot? Just let me know! 🙂"
)

FOLLOWUP_NO_SHOW = (
    "Hi! 👋\n\n"
    "We missed you at the interview today — hope everything is okay!\n\n"
    "No worries, things happen. Would you like to reschedule? "
    "I can set up a new time that works better for you.\n\n"
    "Just let me know! 🙂"
)

FOLLOWUP_SILENT = (
    "Hey! 😊\n\n"
    "I noticed you didn't finish the application — "
    "that's totally fine, no pressure!\n\n"
    "If you got stuck on any question or need more info about the role, "
    "just let me know. I'm happy to help.\n\n"
    "The position is still open if you're interested! 🙂"
)

# ═══ INTERVIEW ═══

INTERVIEW_INVITATION = (
    "Great news — you've been selected for an interview! 🎉\n\n"
    "Here are the details:\n\n"
    "📅 Date: {date}\n"
    "⏰ Time: {time}\n"
    "📍 Platform: Zoom\n"
    "🔗 Link: {zoom_link}\n\n"
    "What to expect:\n"
    "• 30-40 minute video call\n"
    "• Learn about the role in detail\n"
    "• Ask any questions you have\n"
    "• Quick age verification (just show your ID briefly)\n\n"
    "Please join 2-3 minutes early. "
    "Make sure your camera and microphone are working.\n\n"
    "See you there! 🙂"
)

REJECTION_MESSAGE = (
    "Thank you for your interest in our team! 🙏\n\n"
    "Unfortunately, we're not able to move forward with your application at this time.\n\n"
    "If anything changes in the future, feel free to reach out again. "
    "We wish you all the best! 🙂\n\n"
    "——\n"
    "If you know someone with free time during the day, a gaming PC, and decent English — "
    "this could be a great fit for them. Pass it along and they'll thank you for it. 🙌"
)
BTN_SHARE_REFERRAL = "🔗 Share with a friend"

# ═══ OBJECTION RESPONSES ═══

OBJ_WHAT_IS_MODERATION = (
    "Great question! 😊\n\n"
    "As a Live Stream Operator, you'll be working behind the scenes — "
    "you never appear on camera.\n\n"
    "Your role includes:\n"
    "• Setting up streaming equipment and software (OBS)\n"
    "• Managing live chat during streams\n"
    "• Helping streamers with technical issues\n"
    "• Scheduling and organizing stream sessions\n\n"
    "Think of it as a technical + organizational role "
    "for content creators on streaming platforms.\n\n"
    "Would you like to hear more about the compensation?"
)

OBJ_ADULT_CONTENT = (
    "I totally understand your concern! 🙏\n\n"
    "We work with various streaming platforms — similar to Twitch, YouTube Live, etc. "
    "The content varies, but your job is strictly behind the scenes: "
    "technical setup, chat moderation, and scheduling.\n\n"
    "You never appear on camera and you don't create any content yourself.\n\n"
    "Does that help clarify things?"
)

OBJ_SCAM = (
    "Totally fair concern — there are a lot of fake job offers online, "
    "so I'm glad you're cautious! 👍\n\n"
    "Here's why this is different:\n"
    "✅ We NEVER ask for any upfront payment\n"
    "✅ You'll have a video interview on Zoom before starting\n"
    "✅ Payment every Monday in USD, without exception\n"
    "✅ You get a personal mentor during your paid training\n\n"
    "We've been operating for years with a team in 15+ countries.\n\n"
    "Would you like to schedule a quick Zoom call so you can see everything for yourself?"
)

OBJ_WHAT_COMPANY = (
    "We're a talent management agency that works with content creators "
    "and streamers worldwide. 🌍\n\n"
    "Our team is spread across 15+ countries, and we help streamers "
    "with the technical and organizational side of their work.\n\n"
    "I'd be happy to share more details during our Zoom interview — "
    "would you like to schedule one?"
)

OBJ_PAY_TOO_LOW = (
    "I hear you! 💰\n\n"
    "$600-800/month is just the starting range. "
    "Here's how the growth works:\n\n"
    "📈 Month 1: $600-800/month (training + first shifts)\n"
    "📈 Month 2-3: $1,000-1,200/month as you get more experience\n"
    "📈 Top performers: $1,500+/month\n\n"
    "Your income is based on revenue share — "
    "the better you get, the more you earn.\n\n"
    "Would you like to give it a try?"
)

OBJ_NEED_TO_THINK = (
    "Of course, take your time! 🤔\n\n"
    "Just so you know — we have a limited number of interview slots this week, "
    "and spots fill up fast.\n\n"
    "Is there anything specific you'd like me to clarify "
    "that would help you decide?\n\n"
    "I can also reserve a slot for you while you think it over — "
    "no obligation. Would that help?"
)

OBJ_ALREADY_HAVE_JOB = (
    "That's great that you're currently working! 💼\n\n"
    "Many of our operators started this as a side gig alongside their main job. "
    "We have 4 shift options:\n\n"
    "🕐 Morning: 6:00 - 12:00\n"
    "🕐 Day: 12:00 - 18:00\n"
    "🕐 Evening: 18:00 - 00:00\n"
    "🕐 Night: 00:00 - 6:00\n\n"
    "You pick the shift that works for you, 5 days a week. "
    "Some people even transition to this full-time once they see the income potential.\n\n"
    "Which shift would work best with your current schedule?"
)

OBJ_NO_EXPERIENCE = (
    "No worries at all! 🎓\n\n"
    "We provide 5-7 days of paid training ($30 per shift) "
    "where you'll learn everything from scratch:\n"
    "• OBS setup and configuration\n"
    "• Chat moderation tools\n"
    "• Equipment setup\n\n"
    "You'll also get a personal mentor who guides you through everything. "
    "Most of our successful operators had zero experience when they started.\n\n"
    "Shall we schedule your interview?"
)

OBJ_SCHEDULE = (
    "We've got flexible options! ⏰\n\n"
    "We offer 4 different shifts:\n"
    "🕐 Morning: 6:00 - 12:00\n"
    "🕐 Day: 12:00 - 18:00\n"
    "🕐 Evening: 18:00 - 00:00\n"
    "🕐 Night: 00:00 - 6:00\n\n"
    "You choose the one that fits your lifestyle, and you work 5 days a week "
    "with 2 days off.\n\n"
    "Which of these shifts would work best for you?"
)

OBJ_NOT_INTERESTED = (
    "No problem at all! Thanks for letting me know. 🙏\n\n"
    "If you change your mind, or if you know someone who might be interested "
    "in earning $150-400/week working from home — "
    "feel free to send them my way!\n\n"
    "Wishing you all the best! 🙂"
)

OBJ_PRIVACY = (
    "I completely understand your concern. 🔒\n\n"
    "Your information came through a job platform where you posted your profile. "
    "I apologize if the outreach was unexpected.\n\n"
    "We take privacy seriously — we don't share your data with anyone.\n\n"
    "If you're not interested, I'll remove your contact right away. "
    "But if you are open to learning about a remote opportunity "
    "earning $150-400/week — I'd love to share more details. 🙂"
)

OBJ_STUDENT = (
    "Being a student is great! 📚\n\n"
    "Quick question — are you studying in-person (attending classes on campus) "
    "or is it distance/online learning?\n\n"
    "Distance learning students can absolutely do this role — "
    "the flexible schedule makes it a perfect fit.\n\n"
    "Could you let me know your study format?"
)

OBJ_OFFICE = (
    "This is a 100% remote position — no office required! 🏠\n\n"
    "You work from the comfort of your own home. "
    "All you need is a PC/laptop with a stable internet connection.\n\n"
    "Many of our team members appreciate this because:\n"
    "• No commute time or cost\n"
    "• Work in comfortable clothes\n"
    "• Save money on transport and food\n\n"
    "Would you like to proceed with the application?"
)

OBJ_PAYMENT_TRUST = (
    "That's a very reasonable question! 💰\n\n"
    "Here's how our payment works:\n"
    "✅ Payments go out every Monday in USD — no exceptions\n"
    "✅ Your first payment comes after your first training shifts\n"
    "✅ We've been paying our team consistently for years\n\n"
    "During the training period you already earn $30 per shift, "
    "so you'll see real money from day one.\n\n"
    "Would you like to schedule your interview?"
)

OBJ_PASSPORT = (
    "Good question! 📋\n\n"
    "We do a quick age verification during onboarding — "
    "it takes literally 10 seconds on a video call. "
    "You just briefly show your ID to confirm you're 18+.\n\n"
    "We do NOT:\n"
    "❌ Collect copies of documents\n"
    "❌ Store your personal data\n"
    "❌ Ask for financial information\n\n"
    "It's simply a legal requirement to verify age. "
    "Is there anything else you'd like to know?"
)

# ═══ SCREENER ═══

SCREENER_RESPONSE_LANG = "The suggested_response MUST be written in English."

# ═══ AGENT / MODEL (Phase 2) ═══

AGENT_GREETING = (
    "Hi {name}! 👋\n\n"
    "Great that you're interested in our Agent program!\n\n"
    "As a Recruitment Agent, you earn for every person you successfully refer:\n\n"
    "Operators:\n"
    "  • 1st–3rd hire: $50 each\n"
    "  • 4th–6th hire: $75 each\n"
    "  • 7th+ hire: $100 each\n\n"
    "Models:\n"
    "  • $10 per working day for 12 months (passive income!)\n\n"
    "Payments: weekly in USD, $50 minimum payout.\n\n"
    "Let me ask a few quick questions. What is your full name?"
)

MODEL_GREETING = (
    "Hi {name}! 👋\n\n"
    "Thanks for your interest in the Content Creator role!\n\n"
    "We work with streaming platforms and are looking for confident, "
    "creative people to join our international team.\n\n"
    "What we offer:\n"
    "  • Flexible schedule — you choose your hours\n"
    "  • Revenue share from streaming income\n"
    "  • Full training with a personal mentor\n"
    "  • Weekly payments in USD\n"
    "  • Team across 15+ countries\n\n"
    "Let me ask a few quick questions.\n\n"
    "What is your full name?"
)

APPLICATION_RECEIVED = (
    "Thank you for applying! 🙏\n\n"
    "Our team will review your application and get back to you within 24 hours.\n\n"
    "If you have any questions in the meantime, feel free to message us!\n\n"
    "You can return to the main menu anytime by typing /menu."
)

# ═══ INTERVIEW BOOKING ═══

BOOKING_START = (
    "Great news! You've been selected for an interview! 🎉\n\n"
    "We just need a couple more details to book your slot.\n\n"
    "What is your date of birth?\n"
    "Please enter in format: DD.MM.YYYY (e.g. 15.05.1998)"
)
BOOKING_DATE_FAIL = (
    "I couldn't understand that date format.\n"
    "Please enter your date of birth as DD.MM.YYYY (e.g. 15.05.1998)"
)
BOOKING_PHONE = (
    "What is your phone number (with country code)?\n"
    "For example: +639171234567 or +2348012345678"
)
BOOKING_PHONE_FAIL = (
    "That doesn't look like a valid phone number.\n"
    "Please enter your full phone number with country code."
)
BOOKING_EXPERIENCE = (
    "One last question! Do you have any experience with:\n"
    "- Live streaming / content moderation\n"
    "- Customer service / virtual assistant\n"
    "- Any other online/remote work\n\n"
    "If yes, briefly describe. If no, just say 'no experience'."
)
BOOKING_FETCHING_SLOTS = "Looking for available interview times..."
BOOKING_SLOTS_ERROR = (
    "Sorry, I couldn't connect to the scheduling system right now.\n"
    "Our team will reach out to you directly to schedule."
)
BOOKING_NO_SLOTS = (
    "No interview slots are available right now.\n"
    "We'll notify you as soon as new slots open up!"
)
BOOKING_SLOTS_TOO_SOON = (
    "All available slots are too soon to book.\n"
    "New slots should appear tomorrow — we'll let you know!"
)
BOOKING_SLOTS_HEADER = (
    "Here are the nearest available interview times (Manila time, GMT+8):\n\n"
    "Pick one that works best for you:"
)
BOOKING_PREF_MATCH = (
    "Here are slots matching your preference (Manila time, GMT+8):\n\n"
    "Pick one that works for you:"
)
BOOKING_PREF_NOMATCH = (
    "No exact match for that time — here are the nearest available slots (Manila time, GMT+8):\n\n"
    "Pick one that works for you:"
)
BTN_OTHER_TIME = "Other time ⏰"
BOOKING_OTHER_TIME = (
    "No problem! What days and times would work better for you?\n"
    "For example: 'weekday evenings' or 'Saturday morning'"
)
BOOKING_CHECKING = "Checking availability..."
BOOKING_RETRY = "Couldn't verify slot availability. Let me try again..."
BOOKING_SLOT_TAKEN = "That slot was just taken! Here are updated options:"
BOOKING_SLOT_RESERVED = (
    "⚡ That slot was just taken by someone else!\n"
    "Let me show you the next available times. 👇"
)
BOOKING_CONFIRMING = "Confirming your slot..."
BOOKING_PREFERRED_ACK = "Got it! Let me check what's available around that time..."
BOOKING_DATA_ERROR = "Something went wrong loading your data. Our team will contact you directly."
BOOKING_SLOT_CHOSEN = (
    "You've chosen: {display} (Manila time) ✅\n\n"
    "Our admin will review and confirm your booking shortly. 🙏"
)
BTN_CHANGE_SLOT = "🔄 Change slot"
BOOKING_CHANGE_SLOT_PROMPT = "No problem! Let's pick a different time:"
BOOKING_CONFIRMED = (
    "Your interview is confirmed! ✅\n\n"
    "📅 {display}\n"
    "🕐 Manila time (GMT+8)\n\n"
    "The interview is a 30-40 minute video call where we'll:\n"
    "• Walk you through the role in detail\n"
    "• Answer any questions you have\n"
    "• Do a quick age verification\n\n"
    "Please be ready 2-3 minutes before your slot. See you there! 🙂"
)
BOOKING_INVITE = (
    "Invitation to work remotely as a live stream moderator:\n\n"
    "📅 {display}\n\n"
    "🕒 Time zone: GMT +8 (Manila)\n"
    "Please check that the time zone matches your local time.\n\n"
    "💻 Format: Our manager will contact you on the day of your interview. "
    "Please stay in touch and reply to the message.\n"
    "Zoom or Discord app.\n\n"
    "Contacts: @hr_helper31 (Telegram)\n"
    "👉 Send \"+\"  wa.me/14433037260  (WhatsApp)\n\n"
    "If your plans change, please notify the manager who scheduled you.\n\n"
    "See you there!"
)
INTERVIEW_MORNING_CONFIRM = (
    "👋 Hey {name}! Just a reminder — your interview is today at {time} (Manila time, GMT+8).\n\n"
    "Will you be there?"
)
BTN_INTERVIEW_YES = "✅ I'll be there!"
BTN_INTERVIEW_NO = "❌ Can't make it"
INTERVIEW_CONFIRMED_REPLY = "✅ Great, see you soon!"
INTERVIEW_CANCEL_REPLY = (
    "Got it. Please contact @hr_helper31 or send \"+\" to wa.me/14433037260 (WhatsApp) to reschedule."
)
INTERVIEW_1H_REMINDER = (
    "⏰ Your interview starts in 1 hour — {time} Manila time!\n\n"
    "@hr_helper31 will reach out to you via Telegram or WhatsApp. Stay online! 📞"
)
BOOKING_SOFT_REJECT = (
    "Thank you for your patience! Our team will contact you within 24 hours "
    "to discuss next steps."
)
REBOOK_NO_SLOTS = (
    "Sorry, the interview slot you selected is no longer available, "
    "and there are no other open times right now. "
    "Our team will contact you to reschedule."
)
REBOOK_PICK_NEW = (
    "Sorry, the slot you picked was just taken! 😔\n\n"
    "Here are the currently available times:"
)
REBOOK_CHECK_FAIL = "Failed to check availability. Please try again later."
REBOOK_SLOT_TAKEN_AGAIN = "That slot was just taken too! Let me refresh..."
REBOOK_CONFIRMED = (
    "New slot selected: {display} (Manila time) ✅\n"
    "Our admin will review and confirm your booking shortly. 🙏"
)
