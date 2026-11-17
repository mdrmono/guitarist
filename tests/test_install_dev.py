from __future__ import annotations

import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest


@unittest.skipUnless(
    sys.platform in ("linux", "darwin") and shutil.which("bash") and shutil.which("rsync"),
    "The development installer requires a Unix host with Bash and rsync",
)
class DevelopmentInstallerTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory(prefix="guitarist-install-")
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        self.source = self.root / "source checkout"
        self.script = self.source / "scripts" / "install_dev.sh"
        self.script.parent.mkdir(parents=True)
        original = Path(__file__).resolve().parents[1] / "scripts" / "install_dev.sh"
        shutil.copy2(original, self.script)
        (self.source / "__init__.py").write_text("# installer fixture\n")
        for directory in (".git", "tests", "__pycache__"):
            excluded = self.source / directory
            excluded.mkdir()
            (excluded / "excluded.txt").write_text("excluded\n")
        self.test_home = self.root / "home with spaces"
        self.test_home.mkdir()
        data_path = (
            "Library/Application Support/Anki2"
            if sys.platform == "darwin"
            else ".local/share/Anki2"
        )
        self.default_target = self.test_home / data_path / "addons21" / "guitarist"

    def install(self, target: Path, override: str | None = None) -> None:
        target.mkdir(parents=True)
        (target / "obsolete.txt").write_text("obsolete\n")
        cache = target / "__pycache__"
        cache.mkdir()
        (cache / "old.pyc").write_bytes(b"old cache")
        environment = dict(os.environ, HOME=str(self.test_home))
        environment.pop("ANKI_ADDON_TARGET", None)
        if override is not None:
            environment["ANKI_ADDON_TARGET"] = override
        subprocess.run(
            ["bash", str(self.script)], env=environment, check=True,
            capture_output=True, text=True, timeout=30,
        )
        self.assertEqual(
            (target / "__init__.py").read_bytes(),
            (self.source / "__init__.py").read_bytes(),
        )
        self.assertEqual((target / "scripts/install_dev.sh").read_bytes(), self.script.read_bytes())
        for excluded in ("obsolete.txt", ".git", "tests", "__pycache__"):
            self.assertFalse((target / excluded).exists(), excluded)

    def test_native_platform_default(self) -> None:
        self.install(self.default_target)

    def test_empty_override_uses_native_default(self) -> None:
        self.install(self.default_target, "")

    def test_explicit_target_with_spaces(self) -> None:
        custom_target = self.root / "custom add-on target"
        self.install(custom_target, str(custom_target))
        self.assertFalse(self.default_target.exists())
