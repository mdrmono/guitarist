"""Development-only module reloader for Anki sessions."""

from __future__ import annotations

import importlib
import os
import sys
from typing import List


DEV_RELOAD_ENV = "GUITARIST_DEV_RELOAD"

_MODULE_RELOAD_ORDER = (
    "core.chords",
    "core.diagram",
    "core.audio",
    "core.generator",
    "core.settings",
    "integration.collection",
    "ui.dialog",
)


def dev_reload_enabled() -> bool:
    return os.environ.get(DEV_RELOAD_ENV, "").strip().lower() in {
        "1",
        "true",
        "yes",
        "on",
    }


def reload_addon_modules() -> List[str]:
    package_name = __package__.split(".", 1)[0] if __package__ else ""
    if not package_name:
        raise RuntimeError("Can not determine Guitarist package name")

    reloaded: List[str] = []
    for module_path in _MODULE_RELOAD_ORDER:
        module_name = f"{package_name}.{module_path}"
        module = sys.modules.get(module_name)
        if module is None:
            module = importlib.import_module(module_name)
        else:
            module = importlib.reload(module)
        reloaded.append(module.__name__)
    return reloaded
