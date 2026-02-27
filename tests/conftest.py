"""Shared fixtures for bot tests.

Provides mocked Message/CallbackQuery factories, FSM state,
and patches DB + external services so tests run offline.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.fsm.context import FSMContext
from aiogram.fsm.storage.base import StorageKey


# ── Factories ──────────────────────────────────────────────────────────────

def make_message(text="", user_id=123456, username="testuser", first_name="Test"):
    """Create a mocked aiogram Message."""
    msg = MagicMock()
    msg.text = text
    msg.photo = None
    msg.content_type = "text"
    msg.from_user = MagicMock()
    msg.from_user.id = user_id
    msg.from_user.username = username
    msg.from_user.first_name = first_name
    msg.answer = AsyncMock()
    msg.bot = MagicMock()
    msg.bot.send_message = AsyncMock()
    return msg


def make_callback(data="", user_id=123456, username="testuser", first_name="Test"):
    """Create a mocked aiogram CallbackQuery."""
    cb = MagicMock()
    cb.data = data
    cb.from_user = MagicMock()
    cb.from_user.id = user_id
    cb.from_user.username = username
    cb.from_user.first_name = first_name
    cb.answer = AsyncMock()
    cb.message = MagicMock()
    cb.message.answer = AsyncMock()
    cb.message.edit_text = AsyncMock()
    cb.bot = MagicMock()
    cb.bot.send_message = AsyncMock()
    return cb


# ── Fixtures ───────────────────────────────────────────────────────────────

@pytest.fixture
def storage():
    return MemoryStorage()


@pytest.fixture
async def state(storage):
    key = StorageKey(bot_id=1, chat_id=123456, user_id=123456)
    return FSMContext(storage=storage, key=key)


@pytest.fixture(autouse=True)
def patch_db():
    """Mock all DB access so tests don't need a real database."""
    session_mock = AsyncMock()
    session_mock.add = MagicMock()
    session_mock.commit = AsyncMock()
    session_mock.refresh = AsyncMock()
    session_mock.execute = AsyncMock(return_value=MagicMock(scalar_one_or_none=MagicMock(return_value=None)))

    cm = AsyncMock()
    cm.__aenter__ = AsyncMock(return_value=session_mock)
    cm.__aexit__ = AsyncMock(return_value=False)

    with patch("bot.handlers.operator_flow.async_session", return_value=cm), \
         patch("bot.handlers.menu.async_session", return_value=cm):
        yield session_mock


@pytest.fixture(autouse=True)
def patch_config():
    """Provide safe config values for tests."""
    with patch("bot.handlers.operator_flow.config") as cfg, \
         patch("bot.handlers.menu.config") as cfg2:
        cfg.ADMIN_CHAT_ID = 999
        cfg.N8N_WEBHOOK_URL = ""
        cfg2.ADMIN_CHAT_ID = 999
        yield cfg


@pytest.fixture(autouse=True)
def patch_screener():
    """Mock AI screener so tests don't call external APIs."""
    from bot.services.screener import ScreeningResult
    mock_result = ScreeningResult(
        english_score=8, hardware_score=9, availability_score=8,
        motivation_score=7, experience_score=5, overall_score=75,
        recommendation="PASS",
        reasoning="Good candidate — meets all requirements",
        suggested_response="Thank you! We'll be in touch within 24 hours.",
    )
    with patch("bot.handlers.operator_flow.screen_candidate", new_callable=AsyncMock, return_value=mock_result):
        yield mock_result
