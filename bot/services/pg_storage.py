"""Persistent FSM storage backed by PostgreSQL (Neon).

Replaces aiogram's MemoryStorage so candidate progress survives bot restarts.
"""

import json
import logging
from typing import Any, Dict, Optional

from aiogram.fsm.state import State
from aiogram.fsm.storage.base import BaseStorage, StorageKey, StateType

from bot.database.connection import async_session
from bot.database.models import FsmState

logger = logging.getLogger(__name__)


class PostgresStorage(BaseStorage):

    async def set_state(self, key: StorageKey, state: StateType = None) -> None:
        if state is None:
            state_str = None
        elif isinstance(state, str):
            state_str = state
        else:
            state_str = state.state

        async with async_session() as session:
            row = await session.get(FsmState, (key.chat_id, key.user_id, key.bot_id))
            if row:
                row.state = state_str
            else:
                session.add(FsmState(
                    chat_id=key.chat_id,
                    user_id=key.user_id,
                    bot_id=key.bot_id,
                    state=state_str,
                    data="{}",
                ))
            await session.commit()

    async def get_state(self, key: StorageKey) -> Optional[str]:
        async with async_session() as session:
            row = await session.get(FsmState, (key.chat_id, key.user_id, key.bot_id))
            return row.state if row else None

    async def set_data(self, key: StorageKey, data: Dict[str, Any]) -> None:
        data_json = json.dumps(data, ensure_ascii=False) if data else "{}"
        async with async_session() as session:
            row = await session.get(FsmState, (key.chat_id, key.user_id, key.bot_id))
            if row:
                row.data = data_json
            else:
                session.add(FsmState(
                    chat_id=key.chat_id,
                    user_id=key.user_id,
                    bot_id=key.bot_id,
                    data=data_json,
                ))
            await session.commit()

    async def get_data(self, key: StorageKey) -> Dict[str, Any]:
        async with async_session() as session:
            row = await session.get(FsmState, (key.chat_id, key.user_id, key.bot_id))
            if row and row.data:
                try:
                    return json.loads(row.data) if isinstance(row.data, str) else row.data
                except (json.JSONDecodeError, TypeError):
                    return {}
            return {}

    async def close(self) -> None:
        pass
