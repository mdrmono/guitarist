from __future__ import annotations

import unittest

from tests.context import setup_import_path

setup_import_path()

from guitarist.core.settings import (
    GuitaristSettings,
    apply_settings_to_config,
    settings_from_config,
)


class SettingsTests(unittest.TestCase):
    def test_settings_use_defaults_for_missing_config(self) -> None:
        settings = settings_from_config(None)

        self.assertEqual(settings.deck_name, "Guitarist")
        self.assertEqual(settings.note_type_name, "Guitarist Chord")
        self.assertTrue(settings.clear_input_after_add)
        self.assertTrue(settings.keep_unsupported_after_add)
        self.assertEqual(settings.sample_bank_path, "")
        self.assertEqual(settings.strum_speed, "Fast")

    def test_settings_clean_blank_deck_name(self) -> None:
        settings = settings_from_config({"deckName": "  "})

        self.assertEqual(settings.deck_name, "Guitarist")

    def test_settings_clean_blank_note_type_name(self) -> None:
        settings = settings_from_config({"noteTypeName": "  "})

        self.assertEqual(settings.note_type_name, "Guitarist Chord")

    def test_apply_settings_preserves_unknown_config(self) -> None:
        config = {"futureOption": 42}
        settings = GuitaristSettings(
            deck_name="Practice",
            note_type_name="My Guitar Chords",
            clear_input_after_add=False,
            keep_unsupported_after_add=True,
            sample_bank_path=" /tmp/guitar-samples ",
            strum_speed="medium",
        )

        updated = apply_settings_to_config(config, settings)

        self.assertEqual(updated["futureOption"], 42)
        self.assertEqual(updated["deckName"], "Practice")
        self.assertEqual(updated["noteTypeName"], "My Guitar Chords")
        self.assertFalse(updated["clearInputAfterAdd"])
        self.assertTrue(updated["keepUnsupportedAfterAdd"])
        self.assertEqual(updated["sampleBankPath"], "/tmp/guitar-samples")
        self.assertEqual(updated["strumSpeed"], "Medium")

    def test_invalid_strum_speed_uses_default(self) -> None:
        settings = settings_from_config({"strumSpeed": "ludicrous"})

        self.assertEqual(settings.strum_speed, "Fast")


if __name__ == "__main__":
    unittest.main()
