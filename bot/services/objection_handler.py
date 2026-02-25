"""Objection handling based on official HuntMe Objection Handling Guide.

15 common objections with Acknowledge -> Reframe -> Bridge framework.
Rule of One: never push more than once on the same objection.
"""

from typing import Optional

# Each objection: keyword patterns for detection + messenger-style response
OBJECTIONS = {
    "what_is_moderation": {
        "keywords": ["what is", "what do", "what does", "moderator do", "what exactly", "explain the job", "what kind of work"],
        "response": (
            "Great question! 😊\n\n"
            "As a Live Stream Moderator, you'll be working behind the scenes — "
            "you never appear on camera.\n\n"
            "Your role includes:\n"
            "• Setting up streaming equipment and software (OBS)\n"
            "• Managing live chat during streams\n"
            "• Helping streamers with technical issues\n"
            "• Scheduling and organizing stream sessions\n\n"
            "Think of it as a technical + organizational role "
            "for content creators on streaming platforms.\n\n"
            "Would you like to hear more about the compensation?"
        ),
    },
    "adult_content": {
        "keywords": ["adult", "nsfw", "webcam", "only fans", "onlyfans", "sexual", "nude", "explicit", "porn", "xxx", "18+"],
        "response": (
            "I totally understand your concern! 🙏\n\n"
            "We work with various streaming platforms — similar to Twitch, YouTube Live, etc. "
            "The content varies, but your job is strictly behind the scenes: "
            "technical setup, chat moderation, and scheduling.\n\n"
            "You never appear on camera and you don't create any content yourself.\n\n"
            "Does that help clarify things?"
        ),
    },
    "scam": {
        "keywords": ["scam", "legit", "legitimate", "real", "fake", "fraud", "trust", "suspicious", "is this real", "too good"],
        "response": (
            "Totally fair concern — there are a lot of fake job offers online, "
            "so I'm glad you're cautious! 👍\n\n"
            "Here's why this is different:\n"
            "✅ We NEVER ask for any upfront payment\n"
            "✅ You'll have a video interview on Zoom before starting\n"
            "✅ Payment is weekly — every Sunday, without exception\n"
            "✅ You get a personal mentor during your paid training\n\n"
            "We've been operating for years with a team in 15+ countries.\n\n"
            "Would you like to schedule a quick Zoom call so you can see everything for yourself?"
        ),
    },
    "what_company": {
        "keywords": ["what company", "company name", "who are you", "which company", "name of company", "website"],
        "response": (
            "We're a talent management agency that works with content creators "
            "and streamers worldwide. 🌍\n\n"
            "Our team is spread across 15+ countries, and we help streamers "
            "with the technical and organizational side of their work.\n\n"
            "I'd be happy to share more details during our Zoom interview — "
            "would you like to schedule one?"
        ),
    },
    "pay_too_low": {
        "keywords": ["too low", "not enough", "more money", "higher pay", "low salary", "only 150", "150 is low", "pay more"],
        "response": (
            "I hear you! 💰\n\n"
            "$150/week is just the starting point during your first week or two. "
            "Here's how the growth works:\n\n"
            "📈 Week 1-2: $150/week (training + first shifts)\n"
            "📈 Month 1-2: $200-300/week as you get more experience\n"
            "📈 Top performers: $400+/week\n\n"
            "Your income is based on revenue share — "
            "the better you get, the more you earn.\n\n"
            "Many of our top moderators started at $150 and now earn $1,600+/month. "
            "Would you like to give it a try?"
        ),
    },
    "need_to_think": {
        "keywords": ["think about", "need to think", "let me think", "consider", "not sure yet", "decide later", "get back to you"],
        "response": (
            "Of course, take your time! 🤔\n\n"
            "Just so you know — we have a limited number of interview slots this week, "
            "and spots fill up fast.\n\n"
            "Is there anything specific you'd like me to clarify "
            "that would help you decide?\n\n"
            "I can also reserve a slot for you while you think it over — "
            "no obligation. Would that help?"
        ),
    },
    "already_have_job": {
        "keywords": ["already work", "have a job", "employed", "full time job", "day job", "current job"],
        "response": (
            "That's great that you're currently working! 💼\n\n"
            "Many of our moderators started this as a side gig alongside their main job. "
            "We have 4 shift options:\n\n"
            "🕐 Morning: 6:00 - 12:00\n"
            "🕐 Day: 12:00 - 18:00\n"
            "🕐 Evening: 18:00 - 00:00\n"
            "🕐 Night: 00:00 - 6:00\n\n"
            "You pick the shift that works for you, 5 days a week. "
            "Some people even transition to this full-time once they see the income potential.\n\n"
            "Which shift would work best with your current schedule?"
        ),
    },
    "no_obs_experience": {
        "keywords": ["obs", "never used", "don't know obs", "no experience with", "streaming software", "technical"],
        "response": (
            "No worries at all! 🎓\n\n"
            "We provide 5-7 days of paid training ($30 per shift) "
            "where you'll learn everything from scratch:\n"
            "• OBS setup and configuration\n"
            "• Chat moderation tools\n"
            "• Equipment setup\n\n"
            "You'll also get a personal mentor who guides you through everything. "
            "Most of our successful moderators had zero experience when they started.\n\n"
            "Shall we schedule your interview?"
        ),
    },
    "schedule_issues": {
        "keywords": ["night shift", "schedule", "hours don't work", "can't work nights", "only morning", "only evening", "timezone"],
        "response": (
            "We've got flexible options! ⏰\n\n"
            "We offer 4 different shifts:\n"
            "🕐 Morning: 6:00 - 12:00\n"
            "🕐 Day: 12:00 - 18:00\n"
            "🕐 Evening: 18:00 - 00:00\n"
            "🕐 Night: 00:00 - 6:00\n\n"
            "You choose the one that fits your lifestyle, and you work 5 days a week "
            "with 2 days off.\n\n"
            "Which of these shifts would work best for you?"
        ),
    },
    "not_interested": {
        "keywords": ["not interested", "no thanks", "no thank you", "pass", "don't want", "not for me"],
        "response": (
            "No problem at all! Thanks for letting me know. 🙏\n\n"
            "If you change your mind, or if you know someone who might be interested "
            "in earning $150-400/week working from home — "
            "feel free to send them my way!\n\n"
            "Wishing you all the best! 🙂"
        ),
    },
    "privacy_concern": {
        "keywords": ["how did you get", "my number", "my contact", "privacy", "where did you find", "data"],
        "response": (
            "I completely understand your concern. 🔒\n\n"
            "Your information came through a job platform where you posted your profile. "
            "I apologize if the outreach was unexpected.\n\n"
            "We take privacy seriously — we don't share your data with anyone.\n\n"
            "If you're not interested, I'll remove your contact right away. "
            "But if you are open to learning about a remote opportunity "
            "earning $150-400/week — I'd love to share more details. 🙂"
        ),
    },
    "student": {
        "keywords": ["student", "university", "college", "studying", "school", "classes"],
        "response": (
            "Being a student is great! 📚\n\n"
            "Quick question — are you studying in-person (attending classes on campus) "
            "or is it distance/online learning?\n\n"
            "Distance learning students can absolutely do this role — "
            "the flexible schedule makes it a perfect fit.\n\n"
            "Could you let me know your study format?"
        ),
    },
    "office_question": {
        "keywords": ["office", "in person", "come to office", "location", "where is the office", "on-site"],
        "response": (
            "This is a 100% remote position — no office required! 🏠\n\n"
            "You work from the comfort of your own home. "
            "All you need is a PC/laptop with a stable internet connection.\n\n"
            "Many of our team members appreciate this because:\n"
            "• No commute time or cost\n"
            "• Work in comfortable clothes\n"
            "• Save money on transport and food\n\n"
            "Would you like to proceed with the application?"
        ),
    },
    "payment_trust": {
        "keywords": ["how do i know", "will you pay", "guarantee", "proof of payment", "payment proof", "really pay", "when get paid"],
        "response": (
            "That's a very reasonable question! 💰\n\n"
            "Here's how our payment works:\n"
            "✅ Payments go out every Sunday — no exceptions\n"
            "✅ Your first payment comes after your first training shifts\n"
            "✅ We pay via GCash, Wise, or USDT — your choice\n"
            "✅ We've been paying our team consistently for years\n\n"
            "During the training period you already earn $30 per shift, "
            "so you'll see real money from day one.\n\n"
            "Would you like to schedule your interview?"
        ),
    },
    "passport_question": {
        "keywords": ["passport", "need id", "show id", "my id", "send id", "identification", "document", "verify identity", "verification", "personal document"],
        "response": (
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
        ),
    },
}


def detect_objection(text: str) -> Optional[str]:
    """Detect objection type from candidate's free-text message.

    Returns objection key or None if no objection detected.
    """
    text_lower = text.lower()

    best_match: Optional[str] = None
    best_score = 0

    for obj_key, obj_data in OBJECTIONS.items():
        score = 0
        for keyword in obj_data["keywords"]:
            if keyword in text_lower:
                score += len(keyword)  # longer keyword matches = higher confidence

        if score > best_score:
            best_score = score
            best_match = obj_key

    # Require at least one keyword match
    return best_match if best_score > 0 else None


def get_response(objection_type: str) -> Optional[str]:
    """Get template response for an objection type."""
    obj = OBJECTIONS.get(objection_type)
    return obj["response"] if obj else None
