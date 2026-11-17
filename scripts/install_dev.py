"""Copy the working tree into Anki's add-on directory on Windows, macOS or Linux."""

from __future__ import annotations

import argparse
import os
from pathlib import Path
import shutil
import stat
import sys
from typing import Mapping


EXCLUDED_NAMES = frozenset({
    ".git", ".github", ".codex", ".playwright-cli", ".venv", "venv",
    "__pycache__", "tests", "output", "dist", "build",
})


def default_target(
    environ: Mapping[str, str] | None = None,
    platform_name: str | None = None,
) -> Path:
    environment = os.environ if environ is None else environ
    system = sys.platform if platform_name is None else platform_name
    if override := environment.get("ANKI_ADDON_TARGET"):
        return Path(override)
    if system == "win32":
        if not (appdata := environment.get("APPDATA")):
            raise ValueError("APPDATA is unset; specify ANKI_ADDON_TARGET or --target")
        data_folder = Path(appdata)
        if not data_folder.is_absolute():
            raise ValueError("APPDATA must be an absolute path")
        return data_folder / "Anki2" / "addons21" / "guitarist"
    home = Path(environment["HOME"]) if environment.get("HOME") else Path.home()
    data_folder = (
        home / "Library" / "Application Support" / "Anki2"
        if system == "darwin" else home / ".local" / "share" / "Anki2"
    )
    return data_folder / "addons21" / "guitarist"


def excluded(path: Path) -> bool:
    return (
        path.name in EXCLUDED_NAMES
        or path.name == ".env"
        or path.name.startswith(".env.")
        or path.suffix in (".pyc", ".pyo")
    )


def is_link(path: Path) -> bool:
    try:
        metadata = path.lstat()
    except FileNotFoundError:
        return False
    return stat.S_ISLNK(metadata.st_mode) or bool(
        getattr(metadata, "st_file_attributes", 0)
        & getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0)
    )


def remove(path: Path) -> None:
    if path.is_dir():
        if not is_link(path):
            shutil.rmtree(path)
        elif path.is_symlink():
            path.unlink()
        else:
            path.rmdir()  # Remove a Windows junction itself, keeping its target.
    else:
        path.unlink()


def sync_directory(source: Path, target: Path) -> None:
    target.mkdir(parents=True, exist_ok=True)
    entries = {entry.name: entry for entry in source.iterdir() if not excluded(entry)}
    for installed in target.iterdir():
        if installed.name == "__pycache__" or installed.suffix in (".pyc", ".pyo"):
            remove(installed)
        elif installed.name not in entries and not excluded(installed):
            remove(installed)
    for name, entry in entries.items():
        destination = target / name
        # Do not follow an installed link when replacing package files.
        if is_link(destination) or (
            destination.exists() and destination.is_dir() != entry.is_dir()
        ):
            remove(destination)
        if entry.is_dir():
            sync_directory(entry, destination)
        else:
            shutil.copy2(entry, destination)


def install(source: Path, target: Path) -> Path:
    source, target = source.resolve(), target.resolve()
    if source == target or source.is_relative_to(target) or target.is_relative_to(source):
        raise ValueError("The installation target and source checkout must not overlap")
    if target.exists() and not target.is_dir():
        raise ValueError("The installation target must be a directory")
    sync_directory(source, target)
    return target


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--target", type=Path, help="Override ANKI_ADDON_TARGET and the OS default")
    args = parser.parse_args()
    try:
        target = args.target if args.target is not None else default_target()
        installed = install(Path(__file__).resolve().parents[1], target)
    except (OSError, ValueError) as error:
        print(f"Could not install Guitarist: {error}", file=sys.stderr)
        return 1
    print(f"Installed Guitarist into {installed}")
    print("Restart Anki to load the installed code.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
