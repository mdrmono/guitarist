"""Configuration defaults and validation for Guitarist."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping


DEFAULT_DECK_NAME = "Guitarist"
DEFAULT_NOTE_TYPE_NAME = "Guitarist Chord"

DECK_NAME_KEY = "deckName"
CLEAR_INPUT_KEY = "clearInputAfterAdd"
KEEP_UNSUPPORTED_KEY = "keepUnsupportedAfterAdd"


@dataclass(frozen=True)
class GuitaristSettings:
    deck_name: str = DEFAULT_DECK_NAME
    clear_input_after_add: bool = True
    keep_unsupported_after_add: bool = True


def _clean_deck_name(value: Any) -> str:
    if not isinstance(value, str):
        return DEFAULT_DECK_NAME
    value = value.strip()
    return value or DEFAULT_DECK_NAME


def _clean_bool(value: Any, default: bool) -> bool:
    if isinstance(value, bool):
        return value
    return default


def settings_from_config(config: Mapping[str, Any] | None) -> GuitaristSettings:
    if config is None:
        config = {}
    return GuitaristSettings(
        deck_name=_clean_deck_name(config.get(DECK_NAME_KEY)),
        clear_input_after_add=_clean_bool(config.get(CLEAR_INPUT_KEY), True),
        keep_unsupported_after_add=_clean_bool(config.get(KEEP_UNSUPPORTED_KEY), True),
    )


def apply_settings_to_config(
    config: Mapping[str, Any] | None,
    settings: GuitaristSettings,
) -> dict[str, Any]:
    updated = dict(config or {})
    updated[DECK_NAME_KEY] = _clean_deck_name(settings.deck_name)
    updated[CLEAR_INPUT_KEY] = settings.clear_input_after_add
    updated[KEEP_UNSUPPORTED_KEY] = settings.keep_unsupported_after_add
    return updated
