"""Tests for objection detection and response system."""

import pytest

from bot.services.objection_handler import detect_objection, get_response, _OBJ_ATTR


class TestDetectObjection:

    def test_detect_scam(self):
        assert detect_objection("Is this a scam?") == "scam"
        assert detect_objection("this seems too good to be true") == "scam"
        assert detect_objection("is this legit?") == "scam"

    def test_detect_adult_content(self):
        assert detect_objection("Is this related to adult content?") == "adult_content"
        assert detect_objection("Is this webcam stuff?") == "adult_content"
        assert detect_objection("this is nsfw right?") == "adult_content"

    def test_detect_payment_trust(self):
        assert detect_objection("How do I know you will pay me?") == "payment_trust"
        assert detect_objection("is there any proof of payment?") == "payment_trust"

    def test_detect_what_company(self):
        assert detect_objection("What company is this?") == "what_company"
        assert detect_objection("What is the company name?") == "what_company"

    def test_detect_pay_too_low(self):
        assert detect_objection("$150 is too low") == "pay_too_low"
        assert detect_objection("Can I get more money?") == "pay_too_low"

    def test_detect_need_to_think(self):
        assert detect_objection("I need to think about it") == "need_to_think"
        assert detect_objection("Let me consider this") == "need_to_think"

    def test_detect_already_have_job(self):
        assert detect_objection("I already work full time") == "already_have_job"
        assert detect_objection("I have a day job") == "already_have_job"

    def test_detect_no_obs_experience(self):
        assert detect_objection("I've never used OBS before") == "no_obs_experience"
        assert detect_objection("I have no experience with streaming software") == "no_obs_experience"

    def test_detect_schedule_issues(self):
        assert detect_objection("I can't work night shift") == "schedule_issues"
        assert detect_objection("The schedule hours don't work for me") == "schedule_issues"

    def test_detect_not_interested(self):
        assert detect_objection("No thanks, not interested") == "not_interested"
        assert detect_objection("This is not for me") == "not_interested"

    def test_detect_privacy(self):
        assert detect_objection("How did you get my number?") == "privacy_concern"
        assert detect_objection("I'm worried about my privacy") == "privacy_concern"

    def test_detect_student(self):
        assert detect_objection("I'm a university student") == "student"
        assert detect_objection("I'm still in college") == "student"

    def test_detect_office(self):
        assert detect_objection("Where is the office located?") == "office_question"
        assert detect_objection("Do I need to come in person?") == "office_question"

    def test_detect_passport(self):
        assert detect_objection("Do I need to show my passport?") == "passport_question"
        assert detect_objection("Will you ask for my ID?") == "passport_question"

    def test_detect_what_is_moderation(self):
        assert detect_objection("What exactly does a moderator do?") == "what_is_moderation"
        assert detect_objection("Can you explain the job?") == "what_is_moderation"

    def test_no_objection_detected(self):
        assert detect_objection("My name is John") is None
        assert detect_objection("22") is None
        assert detect_objection("Intel Core i5") is None
        assert detect_objection("Yes") is None
        assert detect_objection("I'm ready to start") is None


class TestGetResponse:

    def test_all_objections_have_responses(self):
        """Every objection type must have a non-empty response."""
        for key in _OBJ_ATTR:
            response = get_response(key)
            assert response is not None, f"No response for {key}"
            assert len(response) > 50, f"Response too short for {key}"

    def test_unknown_objection_returns_none(self):
        assert get_response("nonexistent_key") is None

    def test_scam_response_contains_reassurance(self):
        response = get_response("scam")
        assert "never ask" in response.lower() or "upfront" in response.lower()

    def test_adult_response_contains_denial(self):
        response = get_response("adult_content")
        assert "behind the scenes" in response.lower()

    def test_payment_response_contains_sunday(self):
        response = get_response("payment_trust")
        assert "sunday" in response.lower()
