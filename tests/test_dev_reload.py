from __future__ import annotations

import os
import unittest

from tests.context import setup_import_path

setup_import_path()

from guitarist.dev_reload import DEV_RELOAD_ENV, dev_reload_enabled


class DevReloadTests(unittest.TestCase):
    def setUp(self) -> None:
        self._original_value = os.environ.get(DEV_RELOAD_ENV)

    def tearDown(self) -> None:
        if self._original_value is None:
            os.environ.pop(DEV_RELOAD_ENV, None)
        else:
            os.environ[DEV_RELOAD_ENV] = self._original_value

    def test_dev_reload_is_disabled_by_default(self) -> None:
        os.environ.pop(DEV_RELOAD_ENV, None)
        self.assertFalse(dev_reload_enabled())

    def test_dev_reload_accepts_truthy_values(self) -> None:
        for value in ("1", "true", "yes", "on"):
            with self.subTest(value=value):
                os.environ[DEV_RELOAD_ENV] = value
                self.assertTrue(dev_reload_enabled())


if __name__ == "__main__":
    unittest.main()
