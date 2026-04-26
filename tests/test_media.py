from __future__ import annotations

import io
import pathlib
import sys
import unittest
import wave

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2]))

from guitarist.audio import generate_chord_wav
from guitarist.diagram import render_chord_svg
from guitarist.generator import prepare_generation


class MediaGenerationTests(unittest.TestCase):
    def test_svg_contains_chord_metadata(self) -> None:
        prepared = prepare_generation("C")
        self.assertEqual(len(prepared.assets), 1)

        svg = render_chord_svg(prepared.assets[0].voicing)
        self.assertIn("<svg", svg)
        self.assertIn('data-chord="C"', svg)
        self.assertIn("open C major", svg)

    def test_wav_is_playable(self) -> None:
        prepared = prepare_generation("Am")
        wav_bytes = generate_chord_wav(prepared.assets[0].voicing)

        self.assertTrue(wav_bytes.startswith(b"RIFF"))
        with wave.open(io.BytesIO(wav_bytes), "rb") as wav:
            self.assertEqual(wav.getnchannels(), 1)
            self.assertEqual(wav.getsampwidth(), 2)
            self.assertEqual(wav.getframerate(), 44100)
            self.assertGreater(wav.getnframes(), 1000)

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


if __name__ == "__main__":
    unittest.main()
