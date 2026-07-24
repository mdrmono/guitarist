from __future__ import annotations

import unittest
from types import SimpleNamespace
from unittest.mock import Mock, call, patch

from tests.context import setup_import_path

setup_import_path()

from guitarist.integration.collection import (  # noqa: E402
    CARD_CSS,
    CARD_TEMPLATES,
    FIELDS,
    ICON_ASSET_DIR,
    ICON_MEDIA_FILES,
    _write_icon_media,
    ensure_notetype,
    refresh_existing_notetype,
)


class NoteTypeConfigurationTests(unittest.TestCase):
    def test_ensure_notetype_uses_configured_name(self) -> None:
        notetype = {
            "css": CARD_CSS,
            "tmpls": [
                {"name": name, "qfmt": qfmt, "afmt": afmt}
                for name, qfmt, afmt in CARD_TEMPLATES
            ],
        }
        models = Mock()
        models.by_name.return_value = notetype
        models.field_names.return_value = list(FIELDS)
        col = SimpleNamespace(models=models)

        resolved, changes = ensure_notetype(col, "My Guitar Chords")

        models.by_name.assert_called_once_with("My Guitar Chords")
        self.assertIs(resolved, notetype)
        self.assertIsNone(changes)

    def test_refresh_notetype_uses_configured_name(self) -> None:
        models = Mock()
        models.by_name.return_value = None
        col = SimpleNamespace(models=models)

        with patch(
            "guitarist.integration.collection._empty_changes",
            return_value="no changes",
        ):
            changes = refresh_existing_notetype(col, "My Guitar Chords")

        models.by_name.assert_called_once_with("My Guitar Chords")
        self.assertEqual(changes, "no changes")

    def test_refresh_notetype_adds_dual_audio_fields(self) -> None:
        notetype = {
            "css": CARD_CSS,
            "tmpls": [
                {"name": name, "qfmt": qfmt, "afmt": afmt}
                for name, qfmt, afmt in CARD_TEMPLATES
            ],
        }
        models = Mock()
        models.by_name.return_value = notetype
        models.field_names.return_value = list(FIELDS[:-2])
        models.new_field.side_effect = lambda name: name
        models.update_dict.return_value = "updated"
        media = Mock()
        media.write_data.side_effect = lambda name, data: name
        col = SimpleNamespace(models=models, media=media)

        changes = refresh_existing_notetype(col)

        self.assertEqual(changes, "updated")
        self.assertEqual(
            models.add_field.call_args_list,
            [
                call(notetype, "Slow Audio"),
                call(notetype, "Strum Speed"),
            ],
        )
        self.assertEqual(media.write_data.call_count, 4)

    def test_icon_assets_are_written_to_collection_media(self) -> None:
        media = Mock()
        media.write_data.side_effect = lambda name, data: name
        col = SimpleNamespace(media=media)

        _write_icon_media(col)

        self.assertEqual(media.write_data.call_count, 4)
        written_names = [args.args[0] for args in media.write_data.call_args_list]
        self.assertEqual(written_names, list(ICON_MEDIA_FILES))
        for asset_name in ICON_MEDIA_FILES.values():
            icon_data = (ICON_ASSET_DIR / asset_name).read_bytes()
            self.assertTrue(icon_data.startswith(b"<?xml"))

    def test_card_css_selects_speed_specific_icons(self) -> None:
        self.assertIn('data-strum-speed="{{Strum Speed}}"', CARD_TEMPLATES[0][2])
        self.assertNotIn("audio-label", CARD_TEMPLATES[0][2])
        self.assertIn("display: flex", CARD_CSS)
        self.assertIn("gap: 16px", CARD_CSS)
        self.assertIn("_guitarist_strum_fast.svg", CARD_CSS)
        self.assertIn("_guitarist_strum_medium.svg", CARD_CSS)
        self.assertIn("_guitarist_strum_slow.svg", CARD_CSS)
        self.assertIn("_guitarist_strum_note_by_note.svg", CARD_CSS)


if __name__ == "__main__":
    unittest.main()
