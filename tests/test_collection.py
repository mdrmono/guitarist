from __future__ import annotations

import unittest
from types import SimpleNamespace
from unittest.mock import Mock, patch

from tests.context import setup_import_path

setup_import_path()

from guitarist.integration.collection import (  # noqa: E402
    CARD_CSS,
    CARD_TEMPLATES,
    FIELDS,
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


if __name__ == "__main__":
    unittest.main()
