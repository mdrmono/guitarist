from __future__ import annotations

import unittest

from tests.context import setup_import_path

setup_import_path()

from guitarist.core.chords import (
    UnsupportedChord,
    lookup_voicing,
    parse_chord,
    parse_chord_inputs,
    suggest_chords,
)


class ChordParsingTests(unittest.TestCase):
    def test_parse_common_names(self) -> None:
        self.assertEqual(parse_chord("C").normalized, "C")
        self.assertEqual(parse_chord("am").normalized, "Am")
        self.assertEqual(parse_chord("Bb7").normalized, "Bb7")
        self.assertEqual(parse_chord("Gmaj7").normalized, "Gmaj7")

    def test_batch_input_split(self) -> None:
        self.assertEqual(parse_chord_inputs("C, Am\nG7; Dsus4"), ["C", "Am", "G7", "Dsus4"])

    def test_slash_chords_are_not_supported(self) -> None:
        with self.assertRaises(UnsupportedChord):
            parse_chord("C/G")


class VoicingLookupTests(unittest.TestCase):
    def test_plan_examples_have_voicings(self) -> None:
        examples = ["C", "Am", "F#", "Bb7", "Gmaj7", "Dsus4"]
        for example in examples:
            with self.subTest(example=example):
                voicing = lookup_voicing(example)
                self.assertEqual(len(voicing.positions), 6)
                self.assertTrue(any(fret is not None for fret in voicing.positions))

    def test_c_major_open_shape(self) -> None:
        voicing = lookup_voicing("C")
        self.assertEqual(voicing.position_text, "x 3 2 0 1 0")
        self.assertIn("C", voicing.note_names)
        self.assertIn("E", voicing.note_names)
        self.assertIn("G", voicing.note_names)


class ChordSuggestionTests(unittest.TestCase):
    def test_prefix_suggestions(self) -> None:
        suggestions = suggest_chords("gma")
        self.assertGreater(len(suggestions), 0)
        self.assertEqual(suggestions[0].chord, "Gmaj7")

    def test_fuzzy_suggestions(self) -> None:
        suggestions = suggest_chords("bflat7")
        self.assertIn("Bb7", [suggestion.chord for suggestion in suggestions])

    def test_empty_query_has_no_suggestions(self) -> None:
        self.assertEqual(suggest_chords(" "), ())


if __name__ == "__main__":
    unittest.main()
