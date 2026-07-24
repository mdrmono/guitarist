from __future__ import annotations

import io
import math
import os
import struct
import tempfile
import unittest
import wave
from unittest.mock import patch

from tests.context import setup_import_path

setup_import_path()

from guitarist.core.audio import generate_chord_wav, sample_filename_for_midi
from guitarist.core.chords import lookup_voicing
from guitarist.core.diagram import render_chord_svg
from guitarist.core.generator import prepare_generation


class MediaGenerationTests(unittest.TestCase):
    def test_svg_contains_chord_metadata(self) -> None:
        prepared = prepare_generation("C")
        self.assertEqual(len(prepared.assets), 1)

        svg = render_chord_svg(prepared.assets[0].voicing)
        self.assertIn("<svg", svg)
        self.assertIn('data-chord="C"', svg)
        self.assertIn("open C major", svg)

    def test_wav_is_playable(self) -> None:
        wav_bytes = generate_chord_wav(lookup_voicing("Am"))

        self.assertTrue(wav_bytes.startswith(b"RIFF"))
        with wave.open(io.BytesIO(wav_bytes), "rb") as wav:
            self.assertEqual(wav.getnchannels(), 1)
            self.assertEqual(wav.getsampwidth(), 2)
            self.assertEqual(wav.getframerate(), 44100)
            self.assertGreater(wav.getnframes(), 1000)

    def test_wav_synthesis_is_deterministic(self) -> None:
        voicing = lookup_voicing("C")

        first = generate_chord_wav(voicing, duration_seconds=0.25)
        second = generate_chord_wav(voicing, duration_seconds=0.25)

        self.assertEqual(first, second)

    def test_sample_filename_uses_scientific_pitch(self) -> None:
        self.assertEqual(sample_filename_for_midi(40), "E2.wav")
        self.assertEqual(sample_filename_for_midi(61), "Cs4.wav")
        self.assertEqual(sample_filename_for_midi(70), "As4.wav")

    def test_wav_uses_configured_sample_bank(self) -> None:
        voicing = lookup_voicing("C")
        with tempfile.TemporaryDirectory() as bank:
            for midi_note in set(voicing.sounding_midis):
                path = os.path.join(bank, sample_filename_for_midi(midi_note))
                with wave.open(path, "wb") as sample:
                    sample.setnchannels(1)
                    sample.setsampwidth(2)
                    sample.setframerate(44100)
                    frames = [12000] + [0] * 4409
                    sample.writeframes(struct.pack(f"<{len(frames)}h", *frames))

            with patch(
                "guitarist.core.audio._synthesize_string",
                side_effect=AssertionError("synthesizer should not run"),
            ):
                wav_bytes = generate_chord_wav(
                    voicing,
                    duration_seconds=0.25,
                    sample_bank_path=bank,
                )

        with wave.open(io.BytesIO(wav_bytes), "rb") as wav:
            self.assertEqual(wav.getframerate(), 44100)
            self.assertEqual(wav.getnchannels(), 1)
            self.assertGreater(wav.getnframes(), 11025)

    def test_configured_sample_bank_reports_missing_notes(self) -> None:
        with tempfile.TemporaryDirectory() as bank:
            with self.assertRaisesRegex(ValueError, "missing"):
                generate_chord_wav(
                    lookup_voicing("C"),
                    duration_seconds=0.1,
                    sample_bank_path=bank,
                )

    def test_wav_has_plucked_string_decay(self) -> None:
        wav_bytes = generate_chord_wav(lookup_voicing("Em"), duration_seconds=1.4)

        with wave.open(io.BytesIO(wav_bytes), "rb") as wav:
            sample_rate = wav.getframerate()
            frame_count = wav.getnframes()
            samples = struct.unpack(
                f"<{frame_count}h",
                wav.readframes(frame_count),
            )

        def rms(start_seconds: float, end_seconds: float) -> float:
            window = samples[
                int(start_seconds * sample_rate) : int(end_seconds * sample_rate)
            ]
            return math.sqrt(sum(sample * sample for sample in window) / len(window))

        self.assertGreater(rms(0.1, 0.35), rms(0.95, 1.2) * 3.0)

    def test_prepare_generation_tracks_unsupported(self) -> None:
        prepared = prepare_generation("C, C/G, Cadd9")
        self.assertEqual([asset.voicing.chord for asset in prepared.assets], ["C"])
        self.assertEqual(len(prepared.unsupported), 2)

    def test_prepare_generation_accepts_batch_input(self) -> None:
        prepared = prepare_generation("C, Am\nG7; Dm7")
        self.assertEqual(
            [asset.voicing.chord for asset in prepared.assets],
            ["C", "Am", "G7", "Dm7"],
        )
        self.assertEqual(prepared.unsupported, [])

    def test_prepare_generation_creates_selected_and_study_audio(self) -> None:
        prepared = prepare_generation("C", strum_speed="Medium")
        asset = prepared.assets[0]

        self.assertEqual(asset.strum_speed, "Medium")
        self.assertIn("_medium_strum.wav", asset.audio_filename)
        self.assertIn("_study_strum.wav", asset.slow_audio_filename)
        self.assertTrue(asset.audio_wav.startswith(b"RIFF"))
        self.assertTrue(asset.slow_audio_wav.startswith(b"RIFF"))
        with wave.open(io.BytesIO(asset.audio_wav), "rb") as selected:
            selected_frames = selected.getnframes()
        with wave.open(io.BytesIO(asset.slow_audio_wav), "rb") as slow:
            slow_frames = slow.getnframes()
        self.assertGreater(slow_frames, selected_frames)


if __name__ == "__main__":
    unittest.main()
