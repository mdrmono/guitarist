"""Offline WAV synthesis for guitar chord study audio."""

from __future__ import annotations

import io
import math
import random
import struct
import wave
from functools import lru_cache
from pathlib import Path
from typing import List, Sequence, Tuple

from .chords import OPEN_STRING_MIDI, Voicing


STRING_BRIGHTNESS = (0.38, 0.41, 0.45, 0.50, 0.58, 0.62)
STRING_SUSTAIN_SECONDS = (3.2, 3.1, 3.0, 2.8, 2.5, 2.3)
STRING_LEVELS = (1.0, 0.97, 0.94, 0.91, 0.87, 0.84)
BODY_MODES = (
    (105.0, 55.0, 0.52),
    (190.0, 80.0, 0.34),
    (315.0, 110.0, 0.22),
    (480.0, 150.0, 0.14),
)
SAMPLE_NOTE_NAMES = (
    "C",
    "Cs",
    "D",
    "Ds",
    "E",
    "F",
    "Fs",
    "G",
    "Gs",
    "A",
    "As",
    "B",
)


def midi_to_frequency(midi_note: int) -> float:
    return 440.0 * (2.0 ** ((midi_note - 69) / 12.0))


def sample_filename_for_midi(midi_note: int) -> str:
    """Return the sample filename for a MIDI note using scientific octaves."""
    note = SAMPLE_NOTE_NAMES[midi_note % 12]
    octave = midi_note // 12 - 1
    return f"{note}{octave}.wav"


def _sounding_strings(voicing: Voicing) -> List[Tuple[int, int]]:
    strings: List[Tuple[int, int]] = []
    for string_index, (open_midi, fret) in enumerate(
        zip(OPEN_STRING_MIDI, voicing.positions)
    ):
        if fret is not None:
            strings.append((string_index, open_midi + fret))
    return strings


def _excitation_buffer(
    delay_frames: int,
    string_index: int,
    seed: int,
) -> List[float]:
    """Create a deterministic pick impulse with string-specific brightness."""
    rng = random.Random(seed)
    noise = [rng.uniform(-1.0, 1.0) for _ in range(delay_frames)]
    pick_offset = max(1, int(delay_frames * (0.16 + string_index * 0.008)))
    picked = [
        value - 0.62 * noise[(index - pick_offset) % delay_frames]
        for index, value in enumerate(noise)
    ]

    brightness = STRING_BRIGHTNESS[string_index]
    filtered: List[float] = []
    state = 0.0
    for value in picked:
        state += brightness * (value - state)
        filtered.append(state)

    mean = sum(filtered) / len(filtered)
    centered = [value - mean for value in filtered]
    peak = max(0.01, max(abs(value) for value in centered))
    return [value / peak for value in centered]


def _synthesize_string(
    midi_note: int,
    string_index: int,
    frame_count: int,
    sample_rate: int,
) -> List[float]:
    """Synthesize one plucked string with a Karplus-Strong feedback loop."""
    frequency = midi_to_frequency(midi_note)
    # Averaging the current and following delay samples advances the loop by
    # roughly half a sample, so the delay line and all-pass stage compensate.
    exact_delay = sample_rate / frequency + 0.5
    delay_frames = max(2, int(math.floor(exact_delay)))
    fractional_delay = exact_delay - delay_frames
    allpass_coefficient = (1.0 - fractional_delay) / (1.0 + fractional_delay)
    seed = (midi_note * 1_000_003) ^ (string_index * 97_409)
    delay = _excitation_buffer(delay_frames, string_index, seed)

    sustain = STRING_SUSTAIN_SECONDS[string_index]
    loss = math.exp(math.log(0.001) / (frequency * sustain))
    attack_frames = max(1, int(sample_rate * 0.0015))
    output: List[float] = []
    delay_index = 0
    previous = 0.0
    previous_allpass_input = 0.0
    previous_allpass_output = 0.0

    for frame in range(frame_count):
        current = delay[delay_index]
        following = delay[(delay_index + 1) % delay_frames]
        averaged = 0.5 * (current + following)
        fractionally_delayed = (
            allpass_coefficient * averaged
            + previous_allpass_input
            - allpass_coefficient * previous_allpass_output
        )
        previous_allpass_input = averaged
        previous_allpass_output = fractionally_delayed
        delay[delay_index] = loss * fractionally_delayed
        delay_index = (delay_index + 1) % delay_frames

        attack = min(1.0, (frame + 1) / attack_frames)
        bridge_motion = current - previous
        output.append((0.82 * current + 0.38 * bridge_motion) * attack)
        previous = current

    return output


def _apply_body_resonance(samples: Sequence[float], sample_rate: int) -> List[float]:
    """Color the strings with broad acoustic-guitar body resonances."""
    mode_coefficients = []
    for frequency, bandwidth, amount in BODY_MODES:
        angle = 2.0 * math.pi * frequency / sample_rate
        radius = math.exp(-math.pi * bandwidth / sample_rate)
        input_gain = (1.0 - radius) * 2.0 * math.sin(angle)
        mode_coefficients.append(
            (2.0 * radius * math.cos(angle), radius * radius, input_gain, amount)
        )

    mode_states = [[0.0, 0.0] for _ in BODY_MODES]
    previous_input = 0.0
    previous_highpass = 0.0
    tone_state = 0.0
    tone_alpha = 1.0 - math.exp(-2.0 * math.pi * 8_500.0 / sample_rate)
    output: List[float] = []

    for sample in samples:
        highpass = sample - previous_input + 0.995 * previous_highpass
        previous_input = sample
        previous_highpass = highpass

        value = highpass * 0.78
        for state, (coefficient, radius_squared, input_gain, amount) in zip(
            mode_states, mode_coefficients
        ):
            resonated = (
                input_gain * highpass
                + coefficient * state[0]
                - radius_squared * state[1]
            )
            state[1] = state[0]
            state[0] = resonated
            value += amount * resonated

        tone_state += tone_alpha * (value - tone_state)
        output.append(tone_state)

    return output


def _master_audio(samples: Sequence[float], sample_rate: int) -> List[float]:
    peak = max(0.01, max(abs(sample) for sample in samples))
    drive = 1.35 / peak
    shaped = [math.tanh(sample * drive) for sample in samples]
    shaped_peak = max(0.01, max(abs(sample) for sample in shaped))
    gain = 0.88 / shaped_peak

    fade_frames = min(len(shaped), int(sample_rate * 0.08))
    fade_start = len(shaped) - fade_frames
    output: List[float] = []
    for index, sample in enumerate(shaped):
        fade = 1.0
        if index >= fade_start:
            fade = (len(shaped) - index - 1) / max(1, fade_frames - 1)
        output.append(sample * gain * fade)
    return output


@lru_cache(maxsize=128)
def _load_wav_sample(path_text: str, expected_sample_rate: int) -> Tuple[float, ...]:
    path = Path(path_text)
    with wave.open(str(path), "rb") as wav:
        channels = wav.getnchannels()
        sample_width = wav.getsampwidth()
        sample_rate = wav.getframerate()
        frame_count = wav.getnframes()
        frames = wav.readframes(frame_count)

    if channels < 1:
        raise ValueError(f"Sample has no audio channels: {path}")
    if sample_width != 2:
        raise ValueError(f"Sample must use 16-bit PCM audio: {path}")
    if sample_rate != expected_sample_rate:
        raise ValueError(
            f"Sample must use a {expected_sample_rate} Hz sample rate: {path}"
        )

    values = struct.unpack(f"<{frame_count * channels}h", frames)
    if channels == 1:
        return tuple(value / 32768.0 for value in values)

    mono: List[float] = []
    for frame_index in range(frame_count):
        start = frame_index * channels
        channel_values = values[start : start + channels]
        mono.append(sum(channel_values) / (channels * 32768.0))
    return tuple(mono)


def _finish_sample_mix(samples: Sequence[float], sample_rate: int) -> List[float]:
    peak = max(0.01, max(abs(sample) for sample in samples))
    gain = 0.92 / peak
    fade_frames = min(len(samples), int(sample_rate * 0.08))
    fade_start = len(samples) - fade_frames
    output: List[float] = []
    for index, sample in enumerate(samples):
        fade = 1.0
        if index >= fade_start:
            fade = (len(samples) - index - 1) / max(1, fade_frames - 1)
        output.append(sample * gain * fade)
    return output


def _strummed_frame_count(
    sounding_strings: Sequence[Tuple[int, int]],
    sample_rate: int,
    sustain_seconds: float,
    strum_delay_seconds: float,
) -> int:
    first_string_index = sounding_strings[0][0]
    last_string_index = sounding_strings[-1][0]
    strum_span = (last_string_index - first_string_index) * strum_delay_seconds
    return int(sample_rate * (sustain_seconds + strum_span))


def _sampled_chord_audio(
    voicing: Voicing,
    sample_bank_path: str,
    sample_rate: int,
    duration_seconds: float,
    strum_delay_seconds: float,
) -> List[float]:
    bank = Path(sample_bank_path).expanduser()
    if not bank.is_dir():
        raise ValueError(f"Sample bank folder does not exist: {bank}")

    sounding_strings = _sounding_strings(voicing)
    total_frames = _strummed_frame_count(
        sounding_strings,
        sample_rate,
        duration_seconds,
        strum_delay_seconds,
    )
    samples = [0.0] * total_frames
    first_string_index = sounding_strings[0][0]

    for string_index, midi_note in sounding_strings:
        filename = sample_filename_for_midi(midi_note)
        path = bank / filename
        if not path.is_file():
            raise ValueError(f"Sample bank is missing {filename}: {bank}")

        string_audio = _load_wav_sample(str(path.resolve()), sample_rate)
        relative_index = string_index - first_string_index
        start_frame = int(relative_index * strum_delay_seconds * sample_rate)
        available_frames = min(len(string_audio), total_frames - start_frame)
        level = STRING_LEVELS[string_index]
        for offset in range(available_frames):
            samples[start_frame + offset] += string_audio[offset] * level

    return _finish_sample_mix(samples, sample_rate)


def _encode_wav(samples: Sequence[float], sample_rate: int) -> bytes:
    output = io.BytesIO()
    with wave.open(output, "wb") as wav:
        wav.setnchannels(1)
        wav.setsampwidth(2)
        wav.setframerate(sample_rate)
        frames = bytearray()
        for sample in samples:
            clipped = max(-1.0, min(1.0, sample))
            frames.extend(struct.pack("<h", int(clipped * 32767)))
        wav.writeframes(bytes(frames))
    return output.getvalue()


def generate_chord_wav(
    voicing: Voicing,
    sample_rate: int = 44100,
    duration_seconds: float = 2.6,
    strum_delay_seconds: float = 0.028,
    sample_bank_path: str = "",
) -> bytes:
    sounding_strings = _sounding_strings(voicing)
    if not sounding_strings:
        raise ValueError("Can not synthesize a voicing with no sounding notes")

    if sample_bank_path.strip():
        sampled_audio = _sampled_chord_audio(
            voicing,
            sample_bank_path,
            sample_rate,
            duration_seconds,
            strum_delay_seconds,
        )
        return _encode_wav(sampled_audio, sample_rate)

    total_frames = _strummed_frame_count(
        sounding_strings,
        sample_rate,
        duration_seconds,
        strum_delay_seconds,
    )
    samples = [0.0] * total_frames
    first_string_index = sounding_strings[0][0]

    for string_index, midi_note in sounding_strings:
        relative_index = string_index - first_string_index
        start_frame = int(relative_index * strum_delay_seconds * sample_rate)
        string_audio = _synthesize_string(
            midi_note,
            string_index,
            total_frames - start_frame,
            sample_rate,
        )
        level = STRING_LEVELS[string_index]
        for offset, sample in enumerate(string_audio):
            samples[start_frame + offset] += sample * level

    samples = _master_audio(_apply_body_resonance(samples, sample_rate), sample_rate)

    return _encode_wav(samples, sample_rate)
