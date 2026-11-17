"""Exercise the installed add-on in real Anki using a disposable profile."""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import platform
import re
import subprocess
import sys
import tempfile
import traceback
import uuid
import wave
from xml.etree import ElementTree


def exercise_anki(base: Path, output: Path) -> int:
    import anki
    import anki.lang
    import aqt
    from aqt.profiles import ProfileManager
    from aqt.qt import QApplication, QTimer, QT_VERSION_STR

    # Seed an isolated profile so startup does not wait for first-run dialogs.
    anki.lang.set_lang("en")
    manager = ProfileManager(base)
    manager.setupMeta()
    manager.setLang("en")
    manager.create("Guitarist Smoke Test")
    manager.load("Guitarist Smoke Test")
    manager.meta["firstRun"] = False
    manager.meta["suppressUpdate"] = True
    manager.profile["autoSync"] = False
    manager.save()
    manager.db.close()

    app = aqt._run(
        argv=["anki", "-b", str(base), "-p", "Guitarist Smoke Test", "-l", "en"],
        exec=False,
    )
    if app is None:
        raise RuntimeError("Anki did not create an application")
    state = {"stage": "collection", "exit_code": 1}
    timer = QTimer()
    dialog = None
    result = {
        "system": platform.system(), "os_version": platform.platform(),
        "architecture": platform.machine(), "python": platform.python_version(),
        "anki": anki.version, "qt": QT_VERSION_STR,
        "installed_addon": str(base / "addons21/guitarist"),
    }

    def finish(error: str | None = None) -> None:
        if state["stage"] == "finished":
            return
        timer.stop()
        state["stage"] = "finished"
        state["exit_code"] = 1 if error else 0
        result["status"] = "failed" if error else "passed"
        if error:
            result["error"] = error
        (output / "result.json").write_text(json.dumps(result, indent=2) + "\n")
        print(json.dumps(result), flush=True)
        if dialog is not None:
            dialog.reject()
        QTimer.singleShot(0, lambda: app.exit(state["exit_code"]))

    def advance() -> None:
        nonlocal dialog
        try:
            if state["stage"] == "collection":
                if aqt.mw.col is None or aqt.mw.state != "deckBrowser":
                    return
                addon = sys.modules.get("guitarist")
                if addon is None:
                    raise AssertionError("Anki did not load Guitarist")
                expected = base / "addons21/guitarist/__init__.py"
                assert Path(addon.__file__).resolve() == expected.resolve()
                actions = [
                    action for action in aqt.mw.form.menuTools.actions()
                    if action.text() == "Guitarist Chord Generator"
                ]
                assert len(actions) == 1, "Generator Tools action missing or duplicated"
                state["stage"] = "dialog"
                # The real menu handler enters a modal event loop; this timer
                # continues driving the visible dialog inside that loop.
                QTimer.singleShot(0, actions[0].trigger)
            elif state["stage"] == "dialog":
                from guitarist.ui.dialog import ChordGeneratorDialog

                visible = [
                    widget for widget in QApplication.topLevelWidgets()
                    if isinstance(widget, ChordGeneratorDialog) and widget.isVisible()
                ]
                if not visible:
                    return
                dialog = visible[0]
                dialog.input.setPlainText("C")
                assert len(dialog.preview_voicings) == 1
                assert dialog.preview_voicings[0].chord == "C"
                assert dialog.create_button.isEnabled()
                assert dialog.grab().save(str(output / "generator.png"))
                state["stage"] = "note"
                dialog.create_button.click()
            elif state["stage"] == "note":
                if not dialog.create_button.isEnabled() or dialog.input.toPlainText():
                    return
                col = aqt.mw.col
                note_ids = col.find_notes('note:"Guitarist Chord"')
                assert len(note_ids) == 1, note_ids
                note = col.get_note(note_ids[0])
                assert note["Chord"] == "C"
                assert len(note.cards()) == 2
                media = Path(col.media.dir())
                diagram = re.fullmatch(r'<img src="([^"]+)">', note["Diagram"])
                assert diagram is not None
                assert ElementTree.parse(media / diagram[1]).getroot().tag.endswith("svg")
                for field in ("Audio", "Slow Audio"):
                    sound = re.fullmatch(r"\[sound:(.+)\]", note[field])
                    assert sound is not None
                    with wave.open(str(media / sound[1]), "rb") as audio:
                        assert audio.getnframes() > 0
                assert dialog.grab().save(str(output / "note-created.png"))
                result.update(notes=1, cards=2, diagram_valid=True, audio_files_valid=2)
                finish()
        except Exception:
            finish(traceback.format_exc())

    timer.timeout.connect(advance)
    timer.start(100)
    QTimer.singleShot(90_000, lambda: finish("Timed out waiting for " + state["stage"]))
    app.exec()
    if aqt.mw.col is not None:
        aqt.mw.col.close()
    return state["exit_code"]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--require-macos", action="store_true")
    parser.add_argument("--output", type=Path, default=Path("output/playwright/anki-smoke"))
    parser.add_argument("--run-anki", type=Path, help=argparse.SUPPRESS)
    args = parser.parse_args()
    output = args.output.resolve()
    if args.run_anki:
        return exercise_anki(args.run_anki, output)
    if args.require_macos and platform.system() != "Darwin":
        parser.error("This smoke test must run on a native macOS host")

    repo = Path(__file__).resolve().parents[1]
    with tempfile.TemporaryDirectory(prefix="guitarist-smoke-") as temporary:
        test_home = Path(temporary) / "home with spaces"
        test_home.mkdir()
        data_path = (
            "Library/Application Support/Anki2"
            if platform.system() == "Darwin" else ".local/share/Anki2"
        )
        base = test_home / data_path
        environment = dict(os.environ, HOME=str(test_home))
        environment.pop("ANKI_ADDON_TARGET", None)
        subprocess.run(["bash", str(repo / "scripts/install_dev.sh")], env=environment, check=True)
        installed = base / "addons21/guitarist/__init__.py"
        assert installed.read_bytes() == (repo / "__init__.py").read_bytes()
        output.mkdir(parents=True, exist_ok=True)
        environment.update(ANKIDEV="1", ANKI_SINGLE_INSTANCE_KEY=uuid.uuid4().hex)
        with (output / "anki.log").open("w") as log:
            completed = subprocess.run(
                [sys.executable, str(Path(__file__).resolve()), "--run-anki", str(base),
                 "--output", str(output)],
                env=environment, stdout=log, stderr=subprocess.STDOUT, timeout=150,
            )
        print((output / "anki.log").read_text())
        if completed.returncode:
            return completed.returncode
        result = json.loads((output / "result.json").read_text())
        assert result["status"] == "passed"
        print("PASS: native installer, Anki load, Tools action, generator, note/cards, SVG and WAV")
        return 0


if __name__ == "__main__":
    raise SystemExit(main())
