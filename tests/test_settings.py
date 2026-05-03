from __future__ import annotations

import unittest

from tests.context import setup_import_path

setup_import_path()

from guitarist.settings import GuitaristSettings, apply_settings_to_config, settings_from_config


class SettingsTests(unittest.TestCase):
    def test_settings_use_defaults_for_missing_config(self) -> None:
        settings = settings_from_config(None)

        self.assertEqual(settings.deck_name, "Guitarist")
        self.assertTrue(settings.clear_input_after_add)
        self.assertTrue(settings.keep_unsupported_after_add)

    def test_settings_clean_blank_deck_name(self) -> None:
        settings = settings_from_config({"deckName": "  "})

        self.assertEqual(settings.deck_name, "Guitarist")

    def test_apply_settings_preserves_unknown_config(self) -> None:
        config = {"noteTypeName": "Guitarist Chord"}
        settings = GuitaristSettings(
            deck_name="Practice",
            clear_input_after_add=False,
            keep_unsupported_after_add=True,
        )

        updated = apply_settings_to_config(config, settings)

        self.assertEqual(updated["noteTypeName"], "Guitarist Chord")
        self.assertEqual(updated["deckName"], "Practice")
        self.assertFalse(updated["clearInputAfterAdd"])
        self.assertTrue(updated["keepUnsupportedAfterAdd"])


if __name__ == "__main__":
    unittest.main()
