"""Chord parsing and built-in guitar voicings."""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Dict, Iterable, List, Optional, Sequence, Tuple


STANDARD_TUNING = ("E", "A", "D", "G", "B", "E")
OPEN_STRING_MIDI = (40, 45, 50, 55, 59, 64)

NOTE_VALUES = {
    "C": 0,
    "B#": 0,
    "C#": 1,
    "Db": 1,
    "D": 2,
    "D#": 3,
    "Eb": 3,
    "E": 4,
    "Fb": 4,
    "E#": 5,
    "F": 5,
    "F#": 6,
    "Gb": 6,
    "G": 7,
    "G#": 8,
    "Ab": 8,
    "A": 9,
    "A#": 10,
    "Bb": 10,
    "B": 11,
    "Cb": 11,
}

VALUE_TO_SHARP = ("C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B")

QUALITY_ALIASES = {
    "": "major",
    "maj": "major",
    "major": "major",
    "M": "major",
    "m": "minor",
    "min": "minor",
    "minor": "minor",
    "-": "minor",
    "7": "dominant7",
    "dom7": "dominant7",
    "maj7": "major7",
    "M7": "major7",
    "major7": "major7",
    "m7": "minor7",
    "min7": "minor7",
    "minor7": "minor7",
    "-7": "minor7",
    "sus": "sus4",
    "sus4": "sus4",
    "5": "power",
}

QUALITY_SUFFIXES = {
    "major": "",
    "minor": "m",
    "dominant7": "7",
    "major7": "maj7",
    "minor7": "m7",
    "sus4": "sus4",
    "power": "5",
}


class UnsupportedChord(ValueError):
    """Raised when a chord symbol can not be mapped to a v1 voicing."""


@dataclass(frozen=True)
class ChordSymbol:
    requested: str
    root: str
    root_value: int
    quality: str
    bass: Optional[str] = None

    @property
    def normalized(self) -> str:
        suffix = QUALITY_SUFFIXES[self.quality]
        chord = f"{self.root}{suffix}"
        if self.bass:
            chord += f"/{self.bass}"
        return chord


@dataclass(frozen=True)
class Voicing:
    chord: str
    root: str
    quality: str
    positions: Tuple[Optional[int], Optional[int], Optional[int], Optional[int], Optional[int], Optional[int]]
    fingers: Tuple[Optional[int], Optional[int], Optional[int], Optional[int], Optional[int], Optional[int]]
    name: str

    @property
    def sounding_midis(self) -> Tuple[int, ...]:
        notes: List[int] = []
        for open_midi, fret in zip(OPEN_STRING_MIDI, self.positions):
            if fret is not None:
                notes.append(open_midi + fret)
        return tuple(notes)

    @property
    def note_names(self) -> Tuple[str, ...]:
        names: List[str] = []
        seen = set()
        for midi in self.sounding_midis:
            name = VALUE_TO_SHARP[midi % 12]
            if name not in seen:
                names.append(name)
                seen.add(name)
        return tuple(names)

    @property
    def string_note_names(self) -> Tuple[Optional[str], Optional[str], Optional[str], Optional[str], Optional[str], Optional[str]]:
        names: List[Optional[str]] = []
        for open_midi, fret in zip(OPEN_STRING_MIDI, self.positions):
            names.append(None if fret is None else VALUE_TO_SHARP[(open_midi + fret) % 12])
        return tuple(names)  # type: ignore[return-value]

    @property
    def position_text(self) -> str:
        parts: List[str] = []
        for fret in self.positions:
            parts.append("x" if fret is None else str(fret))
        return " ".join(parts)

    @property
    def fingering_text(self) -> str:
        parts: List[str] = []
        for fret, finger in zip(self.positions, self.fingers):
            if fret is None:
                parts.append("x")
            elif fret == 0:
                parts.append("0")
            elif finger is None:
                parts.append("?")
            else:
                parts.append(str(finger))
        return " ".join(parts)


@dataclass(frozen=True)
class _Template:
    quality: str
    name: str
    root_string_value: int
    offsets: Tuple[Optional[int], Optional[int], Optional[int], Optional[int], Optional[int], Optional[int]]
    fingers: Tuple[Optional[int], Optional[int], Optional[int], Optional[int], Optional[int], Optional[int]]
    priority: int


def _normalize_root(letter: str, accidental: str) -> str:
    root = letter.upper()
    if accidental:
        root += "b" if accidental.lower() == "b" else "#"
    return root


def _normalize_quality(token: str) -> str:
    token = token.strip()
    if token in QUALITY_ALIASES:
        return QUALITY_ALIASES[token]
    lowered = token.lower()
    if lowered in QUALITY_ALIASES:
        return QUALITY_ALIASES[lowered]
    raise UnsupportedChord(f"Unsupported chord quality: {token or 'major'}")


def parse_chord(symbol: str) -> ChordSymbol:
    raw = symbol.strip()
    if not raw:
        raise UnsupportedChord("Empty chord symbol")

    match = re.match(r"^([A-Ga-g])([#b]?)([^/]*)((?:/[A-Ga-g][#b]?)?)$", raw)
    if not match:
        raise UnsupportedChord(f"Could not parse chord: {symbol}")

    root = _normalize_root(match.group(1), match.group(2))
    if root not in NOTE_VALUES:
        raise UnsupportedChord(f"Unsupported root: {root}")

    bass_token = match.group(4)
    bass = None
    if bass_token:
        bass_match = re.match(r"^/([A-Ga-g])([#b]?)$", bass_token)
        if not bass_match:
            raise UnsupportedChord(f"Could not parse slash chord: {symbol}")
        bass = _normalize_root(bass_match.group(1), bass_match.group(2))

    quality = _normalize_quality(match.group(3))
    parsed = ChordSymbol(
        requested=raw,
        root=root,
        root_value=NOTE_VALUES[root],
        quality=quality,
        bass=bass,
    )
    if parsed.bass:
        raise UnsupportedChord("Slash chords are not supported in v1")
    return parsed


def parse_chord_inputs(text: str) -> List[str]:
    parts = re.split(r"[,;\n]+", text)
    return [part.strip() for part in parts if part.strip()]


def _positions(values: Sequence[Optional[int]]) -> Tuple[Optional[int], Optional[int], Optional[int], Optional[int], Optional[int], Optional[int]]:
    if len(values) != 6:
        raise ValueError("Voicings must define exactly 6 strings")
    return tuple(values)  # type: ignore[return-value]


OPEN_VOICINGS: Dict[Tuple[int, str], Tuple[Sequence[Optional[int]], Sequence[Optional[int]], str]] = {
    (0, "major"): ([None, 3, 2, 0, 1, 0], [None, 3, 2, None, 1, None], "open C major"),
    (2, "major"): ([None, None, 0, 2, 3, 2], [None, None, None, 1, 3, 2], "open D major"),
    (4, "major"): ([0, 2, 2, 1, 0, 0], [None, 2, 3, 1, None, None], "open E major"),
    (7, "major"): ([3, 2, 0, 0, 0, 3], [2, 1, None, None, None, 3], "open G major"),
    (9, "major"): ([None, 0, 2, 2, 2, 0], [None, None, 1, 2, 3, None], "open A major"),
    (2, "minor"): ([None, None, 0, 2, 3, 1], [None, None, None, 2, 3, 1], "open D minor"),
    (4, "minor"): ([0, 2, 2, 0, 0, 0], [None, 2, 3, None, None, None], "open E minor"),
    (9, "minor"): ([None, 0, 2, 2, 1, 0], [None, None, 2, 3, 1, None], "open A minor"),
    (0, "dominant7"): ([None, 3, 2, 3, 1, 0], [None, 3, 2, 4, 1, None], "open C7"),
    (2, "dominant7"): ([None, None, 0, 2, 1, 2], [None, None, None, 2, 1, 3], "open D7"),
    (4, "dominant7"): ([0, 2, 0, 1, 0, 0], [None, 2, None, 1, None, None], "open E7"),
    (7, "dominant7"): ([3, 2, 0, 0, 0, 1], [3, 2, None, None, None, 1], "open G7"),
    (9, "dominant7"): ([None, 0, 2, 0, 2, 0], [None, None, 2, None, 3, None], "open A7"),
    (11, "dominant7"): ([None, 2, 1, 2, 0, 2], [None, 2, 1, 3, None, 4], "open B7"),
    (0, "major7"): ([None, 3, 2, 0, 0, 0], [None, 3, 2, None, None, None], "open Cmaj7"),
    (2, "major7"): ([None, None, 0, 2, 2, 2], [None, None, None, 1, 2, 3], "open Dmaj7"),
    (4, "major7"): ([0, 2, 1, 1, 0, 0], [None, 3, 1, 2, None, None], "open Emaj7"),
    (7, "major7"): ([3, 2, 0, 0, 0, 2], [3, 1, None, None, None, 2], "open Gmaj7"),
    (9, "major7"): ([None, 0, 2, 1, 2, 0], [None, None, 2, 1, 3, None], "open Amaj7"),
    (2, "minor7"): ([None, None, 0, 2, 1, 1], [None, None, None, 2, 1, 1], "open Dm7"),
    (4, "minor7"): ([0, 2, 0, 0, 0, 0], [None, 2, None, None, None, None], "open Em7"),
    (9, "minor7"): ([None, 0, 2, 0, 1, 0], [None, None, 2, None, 1, None], "open Am7"),
    (2, "sus4"): ([None, None, 0, 2, 3, 3], [None, None, None, 1, 3, 4], "open Dsus4"),
    (4, "sus4"): ([0, 2, 2, 2, 0, 0], [None, 1, 2, 3, None, None], "open Esus4"),
    (9, "sus4"): ([None, 0, 2, 2, 3, 0], [None, None, 1, 2, 3, None], "open Asus4"),
    (2, "power"): ([None, None, 0, 2, 3, None], [None, None, None, 1, 3, None], "open D5"),
    (4, "power"): ([0, 2, 2, None, None, None], [None, 1, 3, None, None, None], "open E5"),
    (9, "power"): ([None, 0, 2, 2, None, None], [None, None, 1, 3, None, None], "open A5"),
}

MOVABLE_TEMPLATES: Tuple[_Template, ...] = (
    _Template("major", "E-shape barre major", NOTE_VALUES["E"], _positions([0, 2, 2, 1, 0, 0]), _positions([1, 3, 4, 2, 1, 1]), 2),
    _Template("major", "A-shape barre major", NOTE_VALUES["A"], _positions([None, 0, 2, 2, 2, 0]), _positions([None, 1, 3, 3, 3, 1]), 1),
    _Template("minor", "E-shape barre minor", NOTE_VALUES["E"], _positions([0, 2, 2, 0, 0, 0]), _positions([1, 3, 4, 1, 1, 1]), 2),
    _Template("minor", "A-shape barre minor", NOTE_VALUES["A"], _positions([None, 0, 2, 2, 1, 0]), _positions([None, 1, 3, 4, 2, 1]), 1),
    _Template("dominant7", "E-shape dominant seventh", NOTE_VALUES["E"], _positions([0, 2, 0, 1, 0, 0]), _positions([1, 3, 1, 2, 1, 1]), 2),
    _Template("dominant7", "A-shape dominant seventh", NOTE_VALUES["A"], _positions([None, 0, 2, 0, 2, 0]), _positions([None, 1, 3, 1, 4, 1]), 1),
    _Template("major7", "E-shape major seventh", NOTE_VALUES["E"], _positions([0, 2, 1, 1, 0, 0]), _positions([1, 4, 2, 3, 1, 1]), 2),
    _Template("major7", "A-shape major seventh", NOTE_VALUES["A"], _positions([None, 0, 2, 1, 2, 0]), _positions([None, 1, 3, 2, 4, 1]), 1),
    _Template("minor7", "E-shape minor seventh", NOTE_VALUES["E"], _positions([0, 2, 0, 0, 0, 0]), _positions([1, 3, 1, 1, 1, 1]), 2),
    _Template("minor7", "A-shape minor seventh", NOTE_VALUES["A"], _positions([None, 0, 2, 0, 1, 0]), _positions([None, 1, 3, 1, 2, 1]), 1),
    _Template("sus4", "E-shape suspended fourth", NOTE_VALUES["E"], _positions([0, 2, 2, 2, 0, 0]), _positions([1, 2, 3, 4, 1, 1]), 2),
    _Template("sus4", "A-shape suspended fourth", NOTE_VALUES["A"], _positions([None, 0, 2, 2, 3, 0]), _positions([None, 1, 2, 3, 4, 1]), 1),
    _Template("power", "E-string power chord", NOTE_VALUES["E"], _positions([0, 2, 2, None, None, None]), _positions([1, 3, 4, None, None, None]), 2),
    _Template("power", "A-string power chord", NOTE_VALUES["A"], _positions([None, 0, 2, 2, None, None]), _positions([None, 1, 3, 4, None, None]), 1),
)


def _open_voicing(symbol: ChordSymbol) -> Optional[Voicing]:
    definition = OPEN_VOICINGS.get((symbol.root_value, symbol.quality))
    if not definition:
        return None
    positions, fingers, name = definition
    return Voicing(
        chord=symbol.normalized,
        root=symbol.root,
        quality=symbol.quality,
        positions=_positions(positions),
        fingers=_positions(fingers),
        name=name,
    )


def _candidate_from_template(symbol: ChordSymbol, template: _Template) -> Voicing:
    root_fret = (symbol.root_value - template.root_string_value) % 12
    positions: List[Optional[int]] = []
    for offset in template.offsets:
        positions.append(None if offset is None else root_fret + offset)
    name = template.name if root_fret > 0 else template.name.replace("barre ", "open ")
    return Voicing(
        chord=symbol.normalized,
        root=symbol.root,
        quality=symbol.quality,
        positions=_positions(positions),
        fingers=template.fingers,
        name=name,
    )


def _score_candidate(template: _Template, voicing: Voicing) -> Tuple[int, int, int, int]:
    fretted = [fret for fret in voicing.positions if fret is not None and fret > 0]
    open_string_count = sum(1 for fret in voicing.positions if fret == 0)
    max_fret = max(fretted) if fretted else 0
    min_fret = min(fretted) if fretted else 0
    return (-open_string_count, max_fret, min_fret, template.priority)


def lookup_voicing(symbol: str) -> Voicing:
    parsed = parse_chord(symbol)

    open_voicing = _open_voicing(parsed)
    if open_voicing:
        return open_voicing

    candidates: List[Tuple[Tuple[int, int, int, int], Voicing]] = []
    for template in MOVABLE_TEMPLATES:
        if template.quality != parsed.quality:
            continue
        voicing = _candidate_from_template(parsed, template)
        if max(fret or 0 for fret in voicing.positions) <= 15:
            candidates.append((_score_candidate(template, voicing), voicing))

    if not candidates:
        raise UnsupportedChord(f"No built-in voicing for {parsed.normalized}")

    candidates.sort(key=lambda item: item[0])
    return candidates[0][1]


def supported_quality_suffixes() -> Iterable[str]:
    return QUALITY_SUFFIXES.values()
