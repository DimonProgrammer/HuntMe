"""Tests for agent redirect flow: decline → agent CTA → agent_flow FSM.

Covers:
- Agent name validation
- Text in button-only states
- Full agent flow (region → english → experience → hours → contact)
- English beginner decline in agent flow
- become_agent redirect from operator decline
- Admin approve/reject callbacks
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from tests.conftest import make_message, make_callback
from bot.handlers.agent_flow import (
    AgentForm,
    agent_name,
    agent_region,
    agent_english,
    agent_experience,
    agent_hours,
    agent_contact,
    agent_button_state_text,
)


# ── Patch agent_flow's config for admin notifications ──

@pytest.fixture(autouse=True)
def patch_agent_config():
    with patch("bot.handlers.agent_flow.config") as cfg:
        cfg.ADMIN_CHAT_ID = 999
        yield cfg


# ═══ NAME VALIDATION ═══

class TestAgentName:

    @pytest.mark.asyncio
    async def test_name_too_short(self, state):
        msg = make_message("A")
        await state.update_data(language="en")
        await state.set_state(AgentForm.waiting_name)
        await agent_name(msg, state)
        msg.answer.assert_called_once()
        # Should stay in waiting_name
        assert await state.get_state() == AgentForm.waiting_name.state

    @pytest.mark.asyncio
    async def test_name_too_long(self, state):
        msg = make_message("A" * 51)
        await state.update_data(language="en")
        await state.set_state(AgentForm.waiting_name)
        await agent_name(msg, state)
        msg.answer.assert_called_once()
        assert await state.get_state() == AgentForm.waiting_name.state

    @pytest.mark.asyncio
    async def test_valid_name_advances_to_region(self, state):
        msg = make_message("John Doe")
        await state.update_data(language="en")
        await state.set_state(AgentForm.waiting_name)
        await agent_name(msg, state)
        assert await state.get_state() == AgentForm.waiting_region.state
        data = await state.get_data()
        assert data["name"] == "John Doe"


# ═══ TEXT IN BUTTON STATES ═══

class TestButtonStates:

    @pytest.mark.asyncio
    async def test_text_in_region_state(self, state):
        msg = make_message("Philippines")
        await state.update_data(language="en")
        await state.set_state(AgentForm.waiting_region)
        await agent_button_state_text(msg, state)
        msg.answer.assert_called_once()
        # Should stay in waiting_region
        assert await state.get_state() == AgentForm.waiting_region.state

    @pytest.mark.asyncio
    async def test_text_in_english_state(self, state):
        msg = make_message("B2")
        await state.update_data(language="en")
        await state.set_state(AgentForm.waiting_english)
        await agent_button_state_text(msg, state)
        msg.answer.assert_called_once()

    @pytest.mark.asyncio
    async def test_text_in_hours_state(self, state):
        msg = make_message("10 hours")
        await state.update_data(language="ru")
        await state.set_state(AgentForm.waiting_hours)
        await agent_button_state_text(msg, state)
        msg.answer.assert_called_once()


# ═══ FULL AGENT FLOW ═══

class TestAgentFlow:

    @pytest.mark.asyncio
    async def test_region_advances_to_english(self, state):
        cb = make_callback("aregion_ph")
        await state.update_data(language="en", name="John")
        await state.set_state(AgentForm.waiting_region)
        await agent_region(cb, state)
        assert await state.get_state() == AgentForm.waiting_english.state
        data = await state.get_data()
        assert data["region"] == "ph"

    @pytest.mark.asyncio
    async def test_english_beginner_declines(self, state):
        cb = make_callback("aeng_beginner")
        await state.update_data(language="en", name="John")
        await state.set_state(AgentForm.waiting_english)
        await agent_english(cb, state)
        # State should be cleared (declined)
        assert await state.get_state() is None

    @pytest.mark.asyncio
    async def test_english_b2_advances_to_experience(self, state):
        cb = make_callback("aeng_b2")
        await state.update_data(language="en", name="John")
        await state.set_state(AgentForm.waiting_english)
        await agent_english(cb, state)
        assert await state.get_state() == AgentForm.waiting_experience.state
        data = await state.get_data()
        assert data["english_level"] == "B2"

    @pytest.mark.asyncio
    async def test_experience_advances_to_hours(self, state):
        msg = make_message("I did some VA work before")
        await state.update_data(language="en", name="John")
        await state.set_state(AgentForm.waiting_experience)
        await agent_experience(msg, state)
        assert await state.get_state() == AgentForm.waiting_hours.state
        data = await state.get_data()
        assert data["recruiting_experience"] == "I did some VA work before"

    @pytest.mark.asyncio
    async def test_hours_advances_to_contact(self, state):
        cb = make_callback("ahours_10-20")
        await state.update_data(language="en", name="John")
        await state.set_state(AgentForm.waiting_hours)
        await agent_hours(cb, state)
        assert await state.get_state() == AgentForm.waiting_contact.state
        data = await state.get_data()
        assert data["available_hours"] == "10-20"

    @pytest.mark.asyncio
    async def test_contact_completes_and_notifies_admin(self, state):
        msg = make_message("@johndoe")
        await state.update_data(
            language="en", name="John Doe", region="ph",
            english_level="B2", recruiting_experience="VA work",
            available_hours="10-20",
        )
        await state.set_state(AgentForm.waiting_contact)
        await agent_contact(msg, state)
        # State cleared after completion
        assert await state.get_state() is None
        # Admin notification sent
        msg.bot.send_message.assert_called_once()
        admin_text = msg.bot.send_message.call_args[0][1]
        assert "[AGENT APPLICATION]" in admin_text
        assert "John Doe" in admin_text
        assert "Philippines" in admin_text


# ═══ BECOME_AGENT REDIRECT ═══

class TestBecomeAgentRedirect:

    @pytest.fixture(autouse=True)
    def patch_redirect_db(self):
        """Patch DB for become_agent handler in operator_flow."""
        session_mock = AsyncMock()
        session_mock.execute = AsyncMock(
            return_value=MagicMock(scalar_one_or_none=MagicMock(return_value=None))
        )
        cm = AsyncMock()
        cm.__aenter__ = AsyncMock(return_value=session_mock)
        cm.__aexit__ = AsyncMock(return_value=False)
        with patch("bot.handlers.operator_flow.async_session", return_value=cm):
            yield

    @pytest.fixture(autouse=True)
    def patch_redirect_config(self):
        with patch("bot.handlers.operator_flow.config") as cfg:
            cfg.ADMIN_CHAT_ID = 999
            cfg.N8N_WEBHOOK_URL = ""
            yield

    @pytest.mark.asyncio
    async def test_redirect_with_name_skips_to_region(self, state):
        """If name is known from operator flow, skip step 1."""
        from bot.handlers.operator_flow import on_become_agent

        cb = make_callback("become_agent")
        await state.update_data(name="Maria", language="ru")

        await on_become_agent(cb, state)

        assert await state.get_state() == AgentForm.waiting_region.state
        data = await state.get_data()
        assert data["name"] == "Maria"
        assert data["language"] == "ru"
        assert data["candidate_type"] == "agent"

    @pytest.mark.asyncio
    async def test_redirect_without_name_starts_from_step1(self, state):
        """If no name in FSM data and no DB record, start from name step."""
        from bot.handlers.operator_flow import on_become_agent

        cb = make_callback("become_agent")
        await state.update_data(language="en")

        await on_become_agent(cb, state)

        assert await state.get_state() == AgentForm.waiting_name.state
        data = await state.get_data()
        assert data["language"] == "en"

    @pytest.mark.asyncio
    async def test_redirect_preserves_ru_language(self, state):
        """Critical: Russian language must be preserved through redirect."""
        from bot.handlers.operator_flow import on_become_agent

        cb = make_callback("become_agent")
        await state.update_data(name="Анна", language="ru", age=35)

        await on_become_agent(cb, state)

        data = await state.get_data()
        assert data["language"] == "ru"


# ═══ ADMIN CALLBACKS ═══

class TestAdminAgentCallbacks:

    @pytest.fixture(autouse=True)
    def patch_admin_deps(self):
        session_mock = AsyncMock()
        cand_mock = MagicMock()
        cand_mock.language = "en"
        cand_mock.status = "screened"
        session_mock.execute = AsyncMock(
            return_value=MagicMock(scalar_one_or_none=MagicMock(return_value=cand_mock))
        )
        session_mock.commit = AsyncMock()
        cm = AsyncMock()
        cm.__aenter__ = AsyncMock(return_value=session_mock)
        cm.__aexit__ = AsyncMock(return_value=False)
        with patch("bot.handlers.admin.async_session", return_value=cm), \
             patch("bot.handlers.admin.config") as cfg:
            cfg.ADMIN_CHAT_ID = 999
            self.cand_mock = cand_mock
            yield

    @pytest.mark.asyncio
    async def test_agent_approve(self):
        from bot.handlers.admin import cb_agent_approve

        cb = make_callback("agentok_123456")
        await cb_agent_approve(cb)

        # Approval message sent to candidate
        cb.bot.send_message.assert_called_once()
        # Admin button updated
        cb.answer.assert_called_once_with("Agent approved ✅")
        # Status updated to active
        assert self.cand_mock.status == "active"

    @pytest.mark.asyncio
    async def test_agent_reject(self):
        from bot.handlers.admin import cb_agent_reject

        cb = make_callback("agentno_123456")
        await cb_agent_reject(cb)

        # Rejection sent
        cb.bot.send_message.assert_called_once()
        cb.answer.assert_called_once_with("Agent rejected ❌")
        assert self.cand_mock.status == "declined"
