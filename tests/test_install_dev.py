from __future__ import annotations

import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest

from scripts.install_dev import default_target, install


class DevelopmentInstallerPathTests(unittest.TestCase):
    def test_platform_defaults(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            home = Path(temporary) / "home"
            appdata = home / "AppData" / "Roaming"
            environment = {"HOME": str(home), "APPDATA": str(appdata)}
            expected = {
                "win32": appdata / "Anki2",
                "darwin": home / "Library" / "Application Support" / "Anki2",
                "linux": home / ".local" / "share" / "Anki2",
            }
            for system, base in expected.items():
                with self.subTest(system=system):
                    self.assertEqual(
                        default_target(environment, system), base / "addons21" / "guitarist",
                    )

    def test_explicit_override_does_not_require_appdata(self) -> None:
        environment = {"ANKI_ADDON_TARGET": "custom add-on directory"}
        self.assertEqual(default_target(environment, "win32"), Path(environment["ANKI_ADDON_TARGET"]))

    def test_missing_appdata_fails_instead_of_guessing(self) -> None:
        with self.assertRaisesRegex(ValueError, "APPDATA is unset"):
            default_target({}, "win32")

    def test_relative_appdata_is_rejected(self) -> None:
        with self.assertRaisesRegex(ValueError, "absolute path"):
            default_target({"APPDATA": "relative folder"}, "win32")


class DevelopmentInstallerTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory(prefix="guitarist-install-")
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        self.repo = Path(__file__).resolve().parents[1]
        self.source = self.root / "source checkout"
        self.script = self.source / "scripts" / "install_dev.py"
        self.script.parent.mkdir(parents=True)
        for name in ("install_dev.py", "install_dev.sh"):
            shutil.copy2(self.repo / "scripts" / name, self.source / "scripts" / name)
        (self.source / "__init__.py").write_text("# installer fixture\n")
        (self.source / "core").mkdir()
        (self.source / "core" / "module.py").write_text("VALUE = 1\n")
        for directory in (".git", "tests", "__pycache__", "output", ".venv"):
            excluded = self.source / directory
            excluded.mkdir()
            (excluded / "excluded.txt").write_text("excluded\n")
        (self.source / ".env").write_text("excluded\n")
        self.test_home = self.root / "home with spaces"
        self.test_home.mkdir()
        self.environment = dict(
            os.environ, HOME=str(self.test_home), USERPROFILE=str(self.test_home),
            APPDATA=str(self.test_home / "AppData" / "Roaming"),
        )
        self.environment.pop("ANKI_ADDON_TARGET", None)
        if sys.platform == "win32":
            data_folder = Path(self.environment["APPDATA"]) / "Anki2"
        elif sys.platform == "darwin":
            data_folder = self.test_home / "Library" / "Application Support" / "Anki2"
        else:
            data_folder = self.test_home / ".local" / "share" / "Anki2"
        self.default_target = data_folder / "addons21" / "guitarist"

    def run_installer(
        self, target: Path, override: str | None = None,
        arguments: tuple[str, ...] = (), shell_wrapper: bool = False,
    ) -> None:
        target.mkdir(parents=True, exist_ok=True)
        (target / "obsolete.txt").write_text("obsolete\n")
        cache = target / "__pycache__"
        cache.mkdir()
        (cache / "old.pyc").write_bytes(b"old cache")
        (target / "old.pyc").write_bytes(b"old cache")
        environment = dict(self.environment)
        if override is not None:
            environment["ANKI_ADDON_TARGET"] = override
        command = (
            ["bash", str(self.source / "scripts" / "install_dev.sh")]
            if shell_wrapper else [sys.executable, str(self.script)]
        )
        subprocess.run(
            command + list(arguments), env=environment, check=True,
            capture_output=True, text=True, timeout=30,
        )
        for name in ("__init__.py", "core/module.py", "scripts/install_dev.py"):
            self.assertEqual((target / name).read_bytes(), (self.source / name).read_bytes())
        for excluded in ("obsolete.txt", "old.pyc", ".git", "tests", "__pycache__", "output", ".venv", ".env"):
            self.assertFalse((target / excluded).exists(), excluded)

    def test_native_platform_default(self) -> None:
        self.run_installer(self.default_target)

    def test_empty_override_uses_native_default(self) -> None:
        self.run_installer(self.default_target, "")

    def test_explicit_target_with_spaces(self) -> None:
        custom_target = self.root / "custom add-on target"
        self.run_installer(custom_target, str(custom_target))
        self.assertFalse(self.default_target.exists())

    def test_command_line_target_takes_precedence(self) -> None:
        target = self.root / "command line target"
        environment_target = self.root / "environment target"
        self.run_installer(target, str(environment_target), ("--target", str(target)))
        self.assertFalse(environment_target.exists())
        self.assertFalse(self.default_target.exists())

    def test_obsolete_file_and_directory_types_are_replaced(self) -> None:
        self.default_target.mkdir(parents=True)
        (self.default_target / "__init__.py").mkdir()
        (self.default_target / "__init__.py" / "obsolete.txt").write_text("obsolete")
        (self.default_target / "core").write_text("old module\n")
        self.run_installer(self.default_target)

    def test_overlapping_destinations_leave_source_untouched(self) -> None:
        marker = self.source / "__init__.py"
        original = marker.read_bytes()
        for target in (self.source, self.source / "nested target", self.root):
            with self.subTest(target=target):
                with self.assertRaisesRegex(ValueError, "overlap"):
                    install(self.source, target)
                self.assertEqual(marker.read_bytes(), original)

    def test_file_destination_is_not_removed(self) -> None:
        target = self.root / "existing file"
        target.write_text("preserve\n")
        with self.assertRaisesRegex(ValueError, "directory"):
            install(self.source, target)
        self.assertEqual(target.read_text(), "preserve\n")

    def test_real_checkout_payload_installs(self) -> None:
        subprocess.run(
            [sys.executable, str(self.repo / "scripts/install_dev.py")],
            env=self.environment, check=True, capture_output=True, timeout=30,
        )
        for name in (
            "__init__.py", "manifest.json", "config.json", "core/audio.py",
            "integration/collection.py", "ui/dialog.py", "dev/reload.py",
            "assets/icons/strum-fast.svg",
        ):
            self.assertEqual(
                (self.default_target / name).read_bytes(), (self.repo / name).read_bytes(),
            )
        for name in (".git", "tests", "output", ".venv"):
            self.assertFalse((self.default_target / name).exists())

    @unittest.skipUnless(sys.platform == "win32", "Windows directory junctions")
    def test_windows_junction_does_not_redirect_writes_or_cleanup(self) -> None:
        outside = self.root / "outside directory"
        outside.mkdir()
        sentinel = outside / "preserve.txt"
        sentinel.write_text("preserve\n")
        self.default_target.mkdir(parents=True)
        subprocess.run(
            ["cmd", "/c", "mklink", "/J", str(self.default_target / "core"), str(outside)],
            check=True, capture_output=True, text=True,
        )
        self.run_installer(self.default_target)
        self.assertEqual(sentinel.read_text(), "preserve\n")
        self.assertFalse((outside / "module.py").exists())

    @unittest.skipUnless(sys.platform != "win32" and shutil.which("bash"), "Unix wrapper")
    def test_unix_wrapper_preserves_default_and_override(self) -> None:
        self.run_installer(self.default_target, shell_wrapper=True)
        custom_target = self.root / "wrapper custom target"
        self.run_installer(custom_target, str(custom_target), shell_wrapper=True)
