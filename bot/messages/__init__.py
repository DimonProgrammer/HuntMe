"""Lightweight i18n — language-specific message modules.

Usage:
    from bot.messages import msg
    m = msg(data.get("language", "en"))
    await message.answer(m.MAIN_MENU_TEXT)
"""

from __future__ import annotations

from types import ModuleType

from bot.messages import en, ru

_MODULES: dict[str, ModuleType] = {"en": en, "ru": ru}


def msg(lang: str | None) -> ModuleType:
    """Return the messages module for given language code."""
    return _MODULES.get(lang or "en", en)


def detect_lang_from_deeplink(param: str) -> str | None:
    """Extract language from deep link param: land_ru_42 -> 'ru', land_42 -> None."""
    if param.startswith("land_ru_"):
        return "ru"
    return None

