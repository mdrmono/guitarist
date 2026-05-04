"""Guitarist Anki add-on entry point."""

from __future__ import annotations


def _register_when_loaded() -> None:
    try:
        from aqt import mw  # type: ignore
    except Exception:
        return

    if mw is None:
        return

    from .ui.dialog import register_hooks

    register_hooks()


_register_when_loaded()
