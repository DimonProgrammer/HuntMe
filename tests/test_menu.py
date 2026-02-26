"""Tests for main menu: /start, navigation, duplicate check, question forwarding."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from bot.handlers.menu import (
    MenuStates,
    cmd_start,
    cmd_menu,
    cb_back_main,
    cb_menu_apply,
    cb_menu_question,
    process_question,
    forward_text_to_admin,
)
from bot.handlers.operator_flow import OperatorForm
from tests.conftest import make_message, make_callback


class TestStartCommand:

    async def test_start_shows_menu(self, state):
        msg = make_message("/start")
        await cmd_start(msg, state)

        msg.answer.assert_called_once()
        text = msg.answer.call_args[0][0]
        assert "Apex Talent" in text
        assert await state.get_state() == MenuStates.main_menu.state

    async def test_start_clears_previous_state(self, state):
        """If user was mid-flow and sends /start, state is cleared."""
        await state.set_state(OperatorForm.waiting_age)
        await state.update_data(name="Old Name")

        msg = make_message("/start")
        await cmd_start(msg, state)

        assert await state.get_state() == MenuStates.main_menu.state
        data = await state.get_data()
        assert "name" not in data

    async def test_start_with_referral(self, state):
        msg = make_message("/start ref_999888")
        await cmd_start(msg, state)

        data = await state.get_data()
        assert data["referrer_tg_id"] == 999888
        assert await state.get_state() == MenuStates.main_menu.state

    async def test_start_with_self_referral_ignored(self, state):
        """User can't refer themselves."""
        msg = make_message("/start ref_123456", user_id=123456)
        await cmd_start(msg, state)

        data = await state.get_data()
        assert "referrer_tg_id" not in data

    async def test_start_with_utm_source(self, state):
        msg = make_message("/start fb_ph")
        await cmd_start(msg, state)

        data = await state.get_data()
        assert data["utm_source"] == "fb_ph"


class TestMenuNavigation:

    async def test_menu_command(self, state):
        msg = make_message("/menu")
        await cmd_menu(msg, state)

        msg.answer.assert_called_once()
        assert await state.get_state() == MenuStates.main_menu.state

    async def test_back_to_main_menu(self, state):
        await state.set_state(OperatorForm.waiting_name)
        cb = make_callback("back_main")
        await cb_back_main(cb, state)

        assert await state.get_state() == MenuStates.main_menu.state
        cb.message.edit_text.assert_called()


class TestApplyButton:

    async def test_apply_starts_operator_flow(self, state):
        """Apply Now → operator greeting → waiting_name state."""
        await state.set_state(MenuStates.main_menu)
        cb = make_callback("menu_apply")

        with patch("bot.handlers.menu._start_operator_flow", new_callable=AsyncMock) as mock_start:
            await cb_menu_apply(cb, state)
            mock_start.assert_called_once()


class TestQuestionForwarding:

    async def test_question_flow(self, state):
        await state.set_state(MenuStates.waiting_question)
        msg = make_message("How long has this company been operating?")
        await process_question(msg, state)

        # Should forward to admin
        msg.bot.send_message.assert_called_once()
        admin_text = msg.bot.send_message.call_args[0][1]
        assert "QUESTION" in admin_text
        assert "How long" in admin_text

    async def test_empty_question_ignored(self, state):
        await state.set_state(MenuStates.waiting_question)
        msg = make_message("")
        await process_question(msg, state)

        msg.bot.send_message.assert_not_called()

    async def test_free_text_in_main_menu_forwarded(self, state):
        """Any text in main menu is forwarded to admin."""
        await state.set_state(MenuStates.main_menu)
        msg = make_message("Hey I have a question about the role")
        await forward_text_to_admin(msg, state)

        msg.bot.send_message.assert_called_once()
        admin_text = msg.bot.send_message.call_args[0][1]
        assert "MESSAGE" in admin_text

    async def test_slash_commands_not_forwarded(self, state):
        """Commands like /start should not be forwarded as messages."""
        await state.set_state(MenuStates.main_menu)
        msg = make_message("/something")
        await forward_text_to_admin(msg, state)

        msg.bot.send_message.assert_not_called()
