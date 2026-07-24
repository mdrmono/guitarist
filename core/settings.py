"""Configuration defaults and validation for Guitarist."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping


DEFAULT_DECK_NAME = "Guitarist"
DEFAULT_NOTE_TYPE_NAME = "Guitarist Chord"
DEFAULT_STRUM_SPEED = "Fast"
STRUM_SPEED_DELAYS = {
    "Fast": 0.035,
    "Medium": 0.075,
    "Slow": 0.150,
}
STUDY_STRUM_DELAY_SECONDS = 0.500

DECK_NAME_KEY = "deckName"
NOTE_TYPE_NAME_KEY = "noteTypeName"
CLEAR_INPUT_KEY = "clearInputAfterAdd"
KEEP_UNSUPPORTED_KEY = "keepUnsupportedAfterAdd"
SAMPLE_BANK_PATH_KEY = "sampleBankPath"
STRUM_SPEED_KEY = "strumSpeed"


@dataclass(frozen=True)
class GuitaristSettings:
    deck_name: str = DEFAULT_DECK_NAME
    note_type_name: str = DEFAULT_NOTE_TYPE_NAME
    clear_input_after_add: bool = True
    keep_unsupported_after_add: bool = True
    sample_bank_path: str = ""
    strum_speed: str = DEFAULT_STRUM_SPEED


def _clean_deck_name(value: Any) -> str:
    if not isinstance(value, str):
        return DEFAULT_DECK_NAME
    value = value.strip()
    return value or DEFAULT_DECK_NAME


def _clean_note_type_name(value: Any) -> str:
    if not isinstance(value, str):
        return DEFAULT_NOTE_TYPE_NAME
    value = value.strip()
    return value or DEFAULT_NOTE_TYPE_NAME


def _clean_bool(value: Any, default: bool) -> bool:
    if isinstance(value, bool):
        return value
    return default


def _clean_sample_bank_path(value: Any) -> str:
    if not isinstance(value, str):
        return ""
    return value.strip()


def normalize_strum_speed(value: Any) -> str:
    if isinstance(value, str):
        requested = value.strip().lower()
        for speed in STRUM_SPEED_DELAYS:
            if speed.lower() == requested:
                return speed
    return DEFAULT_STRUM_SPEED


def strum_delay_for_speed(value: Any) -> float:
    return STRUM_SPEED_DELAYS[normalize_strum_speed(value)]


def settings_from_config(config: Mapping[str, Any] | None) -> GuitaristSettings:
    if config is None:
        config = {}
    return GuitaristSettings(
        deck_name=_clean_deck_name(config.get(DECK_NAME_KEY)),
        note_type_name=_clean_note_type_name(config.get(NOTE_TYPE_NAME_KEY)),
        clear_input_after_add=_clean_bool(config.get(CLEAR_INPUT_KEY), True),
        keep_unsupported_after_add=_clean_bool(config.get(KEEP_UNSUPPORTED_KEY), True),
        sample_bank_path=_clean_sample_bank_path(config.get(SAMPLE_BANK_PATH_KEY)),
        strum_speed=normalize_strum_speed(config.get(STRUM_SPEED_KEY)),
    )


def apply_settings_to_config(
    config: Mapping[str, Any] | None,
    settings: GuitaristSettings,
) -> dict[str, Any]:
    updated = dict(config or {})
    updated[DECK_NAME_KEY] = _clean_deck_name(settings.deck_name)
    updated[NOTE_TYPE_NAME_KEY] = _clean_note_type_name(settings.note_type_name)
    updated[CLEAR_INPUT_KEY] = settings.clear_input_after_add
    updated[KEEP_UNSUPPORTED_KEY] = settings.keep_unsupported_after_add
    updated[SAMPLE_BANK_PATH_KEY] = _clean_sample_bank_path(settings.sample_bank_path)
    updated[STRUM_SPEED_KEY] = normalize_strum_speed(settings.strum_speed)
    return updated
