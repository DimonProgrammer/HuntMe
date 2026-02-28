"""Tests for agent application flow: CRM fields collection.

Covers:
- Agent name validation (fallback step)
- DOB validation (format, underage)
- Phone validation
- Full flow (name → dob → phone → admin notification)
- become_agent redirect from operator decline
- Admin approve/reject callbacks
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from tests.conftest import make_message, make_callback
from bot.handlers.agent_flow import (
    AgentForm,
    agent_name,
    agent_dob,
    agent_phone,
)


# ── Patch agent_flow's config for admin notifications ──

@pytest.fixture(autouse=True)
def patch_agent_config():
    with patch("bot.handlers.agent_flow.config") as cfg, \
         patch("bot.handlers.agent_flow.asyncio.sleep", new_callable=AsyncMock):
        cfg.ADMIN_CHAT_ID = 999
        cfg.AGENT_VIDEO_FILE_ID = ""
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
    async def test_valid_name_advances_to_dob(self, state):
        msg = make_message("John Doe")
        await state.update_data(language="en")
        await state.set_state(AgentForm.waiting_name)
        await agent_name(msg, state)
        assert await state.get_state() == AgentForm.waiting_dob.state
        data = await state.get_data()
        assert data["name"] == "John Doe"


# ═══ DOB VALIDATION ═══

class TestAgentDOB:

    @pytest.mark.asyncio
    async def test_invalid_format_stays(self, state):
        msg = make_message("not a date")
        await state.update_data(language="en", name="John")
        await state.set_state(AgentForm.waiting_dob)
        await agent_dob(msg, state)
        msg.answer.assert_called_once()
        assert await state.get_state() == AgentForm.waiting_dob.state

    @pytest.mark.asyncio
    async def test_underage_declines(self, state):
        msg = make_message("15.05.2015")
        await state.update_data(language="en", name="John")
        await state.set_state(AgentForm.waiting_dob)
        await agent_dob(msg, state)
        # State cleared — declined
        assert await state.get_state() is None

    @pytest.mark.asyncio
    async def test_valid_dob_advances_to_phone(self, state):
        msg = make_message("15.05.1995")
        await state.update_data(language="en", name="John")
        await state.set_state(AgentForm.waiting_dob)
        await agent_dob(msg, state)
        assert await state.get_state() == AgentForm.waiting_phone.state
        data = await state.get_data()
        assert data["dob"] == "15.05.1995"

    @pytest.mark.asyncio
    async def test_slash_format_accepted(self, state):
        msg = make_message("15/05/1995")
        await state.update_data(language="en", name="John")
        await state.set_state(AgentForm.waiting_dob)
        await agent_dob(msg, state)
        assert await state.get_state() == AgentForm.waiting_phone.state

    @pytest.mark.asyncio
    async def test_future_date_rejected(self, state):
        msg = make_message("01.01.2030")
        await state.update_data(language="en", name="John")
        await state.set_state(AgentForm.waiting_dob)
        await agent_dob(msg, state)
        msg.answer.assert_called_once()
        assert await state.get_state() == AgentForm.waiting_dob.state


# ═══ PHONE VALIDATION ═══

class TestAgentPhone:

    @pytest.mark.asyncio
    async def test_invalid_phone_stays(self, state):
        msg = make_message("123")
        await state.update_data(language="en", name="John", dob="15.05.1995")
        await state.set_state(AgentForm.waiting_phone)
        await agent_phone(msg, state)
        msg.answer.assert_called_once()
        assert await state.get_state() == AgentForm.waiting_phone.state

    @pytest.mark.asyncio
    async def test_valid_phone_completes_and_notifies(self, state):
        msg = make_message("+63 917 123 4567")
        await state.update_data(
            language="en", name="John Doe",
            dob="15.05.1995", candidate_type="agent",
        )
        await state.set_state(AgentForm.waiting_phone)
        await agent_phone(msg, state)
        # State cleared
        assert await state.get_state() is None
        # Admin notified
        msg.bot.send_message.assert_called_once()
        admin_text = msg.bot.send_message.call_args[0][1]
        assert "[AGENT APPLICATION]" in admin_text
        assert "John Doe" in admin_text
        assert "15.05.1995" in admin_text
        assert "+63 917 123 4567" in admin_text

    @pytest.mark.asyncio
    async def test_phone_with_dashes_accepted(self, state):
        msg = make_message("+7-912-345-6789")
        await state.update_data(language="ru", name="Иван", dob="01.01.1990")
        await state.set_state(AgentForm.waiting_phone)
        await agent_phone(msg, state)
        assert await state.get_state() is None


# ═══ BECOME_AGENT REDIRECT ═══

class TestBecomeAgentRedirect:

    @pytest.fixture(autouse=True)
    def patch_redirect_db(self):
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

    @pytest.fixture(autouse=True)
    def patch_sleep_and_video(self):
        with patch("bot.handlers.agent_flow.asyncio.sleep", new_callable=AsyncMock), \
             patch("bot.handlers.agent_flow.config") as cfg:
            cfg.ADMIN_CHAT_ID = 999
            cfg.AGENT_VIDEO_FILE_ID = ""
            yield

    @pytest.mark.asyncio
    async def test_redirect_with_name_skips_to_dob(self, state):
        """If name is known from operator flow, skip to DOB."""
        from bot.handlers.operator_flow import on_become_agent

        cb = make_callback("become_agent")
        await state.update_data(name="Maria", language="ru")

        await on_become_agent(cb, state)

        assert await state.get_state() == AgentForm.waiting_dob.state
        data = await state.get_data()
        assert data["name"] == "Maria"
        assert data["language"] == "ru"
        assert data["candidate_type"] == "agent"

    @pytest.mark.asyncio
    async def test_redirect_without_name_starts_from_name(self, state):
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

        cb.bot.send_message.assert_called_once()
        cb.answer.assert_called_once_with("Agent approved ✅")
        assert self.cand_mock.status == "active"

    @pytest.mark.asyncio
    async def test_agent_reject(self):
        from bot.handlers.admin import cb_agent_reject

        cb = make_callback("agentno_123456")
        await cb_agent_reject(cb)

        cb.bot.send_message.assert_called_once()
        cb.answer.assert_called_once_with("Agent rejected ❌")
        assert self.cand_mock.status == "declined"
