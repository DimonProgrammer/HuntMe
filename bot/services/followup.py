"""Follow-up templates and interview invitation based on official HuntMe Messenger Scripts.

5 follow-up scenarios + Zoom interview invitation template.
"""

# --- Follow-up Templates ---

FOLLOWUP_TEMPLATES = {
    "no_response_initial": {
        "delay_hours": 3,
        "message": (
            "Hey! 👋\n\n"
            "Just wanted to follow up — did you get a chance to look at the details "
            "I sent about the Live Stream Moderator position?\n\n"
            "We still have a few interview slots available this week. "
            "Let me know if you're interested and I'll get you set up! 😊"
        ),
    },
    "no_response_followup": {
        "delay_hours": 24,
        "message": (
            "Hi again! 🙂\n\n"
            "I know you're probably busy — just a quick reminder that "
            "we're looking for moderators to start next week.\n\n"
            "Starting pay is $600-800/month in USD, fully remote, and we provide all the training.\n\n"
            "If you're interested, just reply with \"Yes\" and I'll send you the next steps. "
            "If not, no worries at all! 🙏"
        ),
    },
    "thinking_about_it": {
        "delay_hours": 12,
        "message": (
            "Hey! Just checking in 😊\n\n"
            "Have you had a chance to think about the moderator position?\n\n"
            "I reserved an interview slot for you — it's a quick 15-min Zoom call "
            "where we explain everything in detail and answer all your questions.\n\n"
            "Would you like to keep the slot? Just let me know! 🙂"
        ),
    },
    "no_show_interview": {
        "delay_hours": 1,
        "message": (
            "Hi! 👋\n\n"
            "We missed you at the interview today — hope everything is okay!\n\n"
            "No worries, things happen. Would you like to reschedule? "
            "I can set up a new time that works better for you.\n\n"
            "Just let me know! 🙂"
        ),
    },
    "silent_after_questions": {
        "delay_hours": 4,
        "message": (
            "Hey! 😊\n\n"
            "I noticed you didn't finish the application — "
            "that's totally fine, no pressure!\n\n"
            "If you got stuck on any question or need more info about the role, "
            "just let me know. I'm happy to help.\n\n"
            "The position is still open if you're interested! 🙂"
        ),
    },
}


# --- Interview Invitation ---

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

# --- Value Proposition Message (Warm — candidate came to us) ---

WARM_GREETING = (
    "Hi {name}! 👋\n\n"
    "Thanks for reaching out! I'm glad you're interested in the position.\n\n"
    "We're a talent management agency that works with content creators "
    "on streaming platforms. We're looking for Live Stream Moderators "
    "to join our remote team.\n\n"
    "Here's a quick overview:\n\n"
    "💰 Starting pay: $600-800/month in USD\n"
    "📈 Growth: $1,000-1,500+/month within 1-2 months\n"
    "🏠 100% remote — work from home\n"
    "📅 Schedule: 5/2, 6-8 hours/day, you choose your shift\n"
    "🎓 Paid training: 5-7 days with a personal mentor\n"
    "💵 Weekly payments in USD\n\n"
    "Your role: technical setup (OBS), chat moderation, "
    "scheduling — all behind the scenes. You never appear on camera.\n\n"
    "Let me ask you a few quick questions to see if this is a good fit. "
    "It'll take about 2 minutes! 🙂\n\n"
    "What is your full name?"
)

# --- Decline Messages ---

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

# --- Agent Greeting ---

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

# --- Model Greeting ---

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

# --- Application Received (agent/model) ---

APPLICATION_RECEIVED = (
    "Thank you for applying! 🙏\n\n"
    "Our team will review your application and get back to you within 24 hours.\n\n"
    "If you have any questions in the meantime, feel free to message us!\n\n"
    "You can return to the main menu anytime by typing /menu."
)
