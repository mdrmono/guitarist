from __future__ import annotations

import pathlib
import sys


def setup_import_path() -> None:
    package_parent = pathlib.Path(__file__).resolve().parents[2]
    package_parent_text = str(package_parent)
    if package_parent_text not in sys.path:
        sys.path.insert(0, package_parent_text)
