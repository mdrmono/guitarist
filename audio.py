"""Offline WAV synthesis for guitar chord study audio."""

from __future__ import annotations

import io
import math
import struct
import wave
from typing import List

from .chords import Voicing


def midi_to_frequency(midi_note: int) -> float:
    return 440.0 * (2.0 ** ((midi_note - 69) / 12.0))


def _pluck_sample(frequency: float, t: float) -> float:
    if t < 0:
        return 0.0
    attack = min(1.0, t / 0.018)
    decay = math.exp(-2.25 * t)
    body = (
        math.sin(2.0 * math.pi * frequency * t) * 0.68
        + math.sin(2.0 * math.pi * frequency * 2.0 * t) * 0.22
        + math.sin(2.0 * math.pi * frequency * 3.0 * t) * 0.10
    )
    shimmer = math.sin(2.0 * math.pi * frequency * 1.006 * t) * 0.08
    return (body + shimmer) * attack * decay


def generate_chord_wav(
    voicing: Voicing,
    sample_rate: int = 44100,
    duration_seconds: float = 2.2,
    strum_delay_seconds: float = 0.038,
) -> bytes:
    midis = voicing.sounding_midis
    if not midis:
        raise ValueError("Can not synthesize a voicing with no sounding notes")

    total_frames = int(sample_rate * duration_seconds)
    frequencies = [midi_to_frequency(midi) for midi in midis]
    starts = [idx * strum_delay_seconds for idx in range(len(frequencies))]
    samples: List[float] = []

    for frame in range(total_frames):
        now = frame / sample_rate
        value = 0.0
        for frequency, start in zip(frequencies, starts):
            value += _pluck_sample(frequency, now - start)
        samples.append(value / max(1, len(frequencies)))

    peak = max(0.01, max(abs(sample) for sample in samples))
    gain = 0.82 / peak

    output = io.BytesIO()
    with wave.open(output, "wb") as wav:
        wav.setnchannels(1)
        wav.setsampwidth(2)
        wav.setframerate(sample_rate)
        frames = bytearray()
        for sample in samples:
            clipped = max(-1.0, min(1.0, sample * gain))
            frames.extend(struct.pack("<h", int(clipped * 32767)))
        wav.writeframes(bytes(frames))

    return output.getvalue()
