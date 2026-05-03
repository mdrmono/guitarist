"""Development-only module reloader for Anki sessions."""

from __future__ import annotations

import importlib
import os
import sys
from typing import List


DEV_RELOAD_ENV = "GUITARIST_DEV_RELOAD"

_MODULE_RELOAD_ORDER = (
    "chords",
    "diagram",
    "audio",
    "generator",
    "anki_integration",
    "dialog",
)


def dev_reload_enabled() -> bool:
    return os.environ.get(DEV_RELOAD_ENV, "").strip().lower() in {
        "1",
        "true",
        "yes",
        "on",
    }


def reload_addon_modules() -> List[str]:
    package_name = __package__
    if not package_name:
        raise RuntimeError("Can not determine Guitarist package name")

    reloaded: List[str] = []
    for module_basename in _MODULE_RELOAD_ORDER:
        module_name = f"{package_name}.{module_basename}"
        module = sys.modules.get(module_name)
        if module is None:
            module = importlib.import_module(module_name)
        else:
            module = importlib.reload(module)
        reloaded.append(module.__name__)
    return reloaded
