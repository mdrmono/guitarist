"""Core generation pipeline for chord assets."""

from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass
from typing import List

from .audio import generate_chord_wav
from .chords import UnsupportedChord, Voicing, lookup_voicing, parse_chord_inputs
from .diagram import render_chord_svg
from .settings import (
    DEFAULT_STRUM_SPEED,
    STUDY_STRUM_DELAY_SECONDS,
    normalize_strum_speed,
    strum_delay_for_speed,
)


@dataclass(frozen=True)
class UnsupportedInput:
    requested: str
    reason: str


@dataclass(frozen=True)
class ChordAsset:
    requested: str
    voicing: Voicing
    diagram_svg: str
    audio_wav: bytes
    diagram_filename: str
    audio_filename: str
    slow_audio_wav: bytes
    slow_audio_filename: str
    strum_speed: str


@dataclass(frozen=True)
class PreparedGeneration:
    assets: List[ChordAsset]
    unsupported: List[UnsupportedInput]


def _safe_stem(chord: str, positions: str) -> str:
    readable = chord.replace("#", "sharp").replace("b", "flat")
    readable = re.sub(r"[^A-Za-z0-9]+", "_", readable).strip("_").lower()
    digest = hashlib.sha1(f"{chord}:{positions}".encode("utf-8")).hexdigest()[:10]
    return f"guitarist_{readable}_{digest}"


def build_chord_asset(
    requested: str,
    sample_bank_path: str = "",
    strum_speed: str = DEFAULT_STRUM_SPEED,
) -> ChordAsset:
    voicing = lookup_voicing(requested)
    stem = _safe_stem(voicing.chord, voicing.position_text)
    normalized_speed = normalize_strum_speed(strum_speed)
    selected_delay = strum_delay_for_speed(normalized_speed)
    return ChordAsset(
        requested=requested,
        voicing=voicing,
        diagram_svg=render_chord_svg(voicing),
        audio_wav=generate_chord_wav(
            voicing,
            strum_delay_seconds=selected_delay,
            sample_bank_path=sample_bank_path,
        ),
        diagram_filename=f"{stem}.svg",
        audio_filename=f"{stem}_{normalized_speed.lower()}_strum.wav",
        slow_audio_wav=generate_chord_wav(
            voicing,
            strum_delay_seconds=STUDY_STRUM_DELAY_SECONDS,
            sample_bank_path=sample_bank_path,
        ),
        slow_audio_filename=f"{stem}_study_strum.wav",
        strum_speed=normalized_speed,
    )


def prepare_generation(
    input_text: str,
    sample_bank_path: str = "",
    strum_speed: str = DEFAULT_STRUM_SPEED,
) -> PreparedGeneration:
    assets: List[ChordAsset] = []
    unsupported: List[UnsupportedInput] = []
    for requested in parse_chord_inputs(input_text):
        try:
            assets.append(build_chord_asset(requested, sample_bank_path, strum_speed))
        except UnsupportedChord as exc:
            unsupported.append(UnsupportedInput(requested=requested, reason=str(exc)))
    return PreparedGeneration(assets=assets, unsupported=unsupported)
