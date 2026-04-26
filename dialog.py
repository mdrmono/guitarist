"""Qt dialog and Anki UI hooks for the Guitarist add-on."""

from __future__ import annotations

from typing import Any, List, Optional

from aqt import gui_hooks, mw  # type: ignore
from aqt.operations import CollectionOp  # type: ignore
from aqt.qt import (  # type: ignore
    QAction,
    QBrush,
    QColor,
    QDialog,
    QFont,
    QFrame,
    QHBoxLayout,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QPainter,
    QPen,
    QPlainTextEdit,
    QPushButton,
    QRectF,
    QTabWidget,
    QTextCursor,
    Qt,
    QVBoxLayout,
    QWidget,
)
from aqt.utils import qconnect, showInfo, showWarning, tooltip  # type: ignore

from .anki_integration import (
    AddChordsResult,
    add_chord_notes,
    preview_inputs,
    refresh_existing_notetype,
)
from .chords import Voicing, lookup_voicing, parse_chord_inputs, suggest_chords


def _align_center() -> Any:
    alignment = getattr(Qt, "AlignmentFlag", Qt)
    return getattr(alignment, "AlignCenter")


def _antialiasing() -> Any:
    render_hint = getattr(QPainter, "RenderHint", QPainter)
    return getattr(render_hint, "Antialiasing")


def _keep_anchor() -> Any:
    move_mode = getattr(QTextCursor, "MoveMode", QTextCursor)
    return getattr(move_mode, "KeepAnchor")


def _user_role() -> Any:
    item_role = getattr(Qt, "ItemDataRole", Qt)
    return getattr(item_role, "UserRole")


class ChordPreviewWidget(QWidget):
    def __init__(self, parent: Any = None) -> None:
        super().__init__(parent)
        self._voicing: Optional[Voicing] = None
        self.setMinimumSize(230, 310)

    def set_voicing(self, voicing: Optional[Voicing]) -> None:
        self._voicing = voicing
        self.update()

    def paintEvent(self, event: Any) -> None:
        painter = QPainter(self)
        painter.setRenderHint(_antialiasing())
        painter.fillRect(self.rect(), QColor("#2b2b2b"))

        panel = QRectF(12, 12, self.width() - 24, self.height() - 24)
        painter.setPen(QPen(QColor("#3a3d4b"), 1))
        painter.setBrush(QBrush(QColor("#f4f1ec")))
        painter.drawRoundedRect(panel, 10, 10)

        if self._voicing is None:
            painter.setPen(QColor("#6a6f82"))
            painter.setFont(QFont("Arial", 13))
            painter.drawText(panel, _align_center(), "Type a chord")
            painter.end()
            return

        voicing = self._voicing
        painter.setPen(QColor("#0f1118"))
        title_font = QFont("Arial", 22)
        title_font.setBold(True)
        painter.setFont(title_font)
        painter.drawText(QRectF(panel.left(), panel.top() + 12, panel.width(), 36), _align_center(), voicing.chord)

        left = panel.left() + 48
        top = panel.top() + 88
        string_gap = (panel.width() - 96) / 5
        fret_gap = 34
        bottom = top + fret_gap * 5
        right = left + string_gap * 5
        fretted = [fret for fret in voicing.positions if fret is not None and fret > 0]
        base_fret = 1 if not fretted or max(fretted) <= 4 else min(fretted)

        painter.setPen(QPen(QColor("#171a22"), 2))
        for idx in range(6):
            x = left + string_gap * idx
            painter.drawLine(int(x), int(top), int(x), int(bottom))
        for idx in range(6):
            y = top + fret_gap * idx
            width = 5 if idx == 0 and base_fret == 1 else 2
            painter.setPen(QPen(QColor("#171a22"), width))
            painter.drawLine(int(left), int(y), int(right), int(y))

        text_font = QFont("Arial", 11)
        marker_font = QFont("Arial", 14)
        marker_font.setBold(True)
        painter.setFont(marker_font)
        for string_idx, fret in enumerate(voicing.positions):
            x = left + string_gap * string_idx
            marker = "x" if fret is None else "o" if fret == 0 else ""
            if marker:
                painter.setPen(QColor("#111318"))
                painter.drawText(QRectF(x - 12, top - 31, 24, 22), _align_center(), marker)

        for string_idx, fret in enumerate(voicing.positions):
            if fret is None or fret == 0:
                continue
            relative_fret = fret - base_fret + 1
            if relative_fret < 1 or relative_fret > 5:
                continue
            x = left + string_gap * string_idx
            y = top + fret_gap * (relative_fret - 0.5)
            painter.setPen(QPen(QColor("#4c44b8"), 1))
            painter.setBrush(QBrush(QColor("#5f55d8")))
            painter.drawEllipse(QRectF(x - 14, y - 14, 28, 28))
            painter.setPen(QColor("#ffffff"))
            painter.setFont(marker_font)
            finger = voicing.fingers[string_idx]
            if finger is not None:
                painter.drawText(QRectF(x - 12, y - 11, 24, 22), _align_center(), str(finger))

        painter.setFont(text_font)
        painter.setPen(QColor("#111318"))
        for string_idx, note in enumerate(voicing.string_note_names):
            if note:
                x = left + string_gap * string_idx
                painter.drawText(QRectF(x - 18, bottom + 16, 36, 20), _align_center(), note)
        painter.end()


STYLE_SHEET = """
QDialog {
  background: #2b2b2b;
  color: #f4f4fb;
  font-family: Arial, Helvetica, sans-serif;
}
QLabel {
  color: #f4f4fb;
}
QLabel#Title {
  font-size: 24px;
  font-weight: 700;
}
QLabel#Subtitle {
  color: #a7a1ff;
  font-size: 13px;
}
QFrame#Card {
  background: #303030;
  border: 1px solid #404040;
  border-radius: 8px;
}
QPlainTextEdit,
QListWidget {
  background: #353535;
  border: 1px solid #474747;
  border-radius: 6px;
  color: #f4f4fb;
  selection-background-color: #544cc8;
  padding: 6px;
}
QTabWidget::pane {
  border: 1px solid #404040;
  border-radius: 8px;
  background: #2b2b2b;
}
QTabBar::tab {
  background: #353535;
  border: 1px solid #404040;
  color: #d9d8e8;
  min-width: 92px;
  padding: 8px 12px;
}
QTabBar::tab:selected {
  color: #ffffff;
  border-bottom: 2px solid #8d83ff;
}
QPushButton {
  background: #383838;
  border: 1px solid #4a4a4a;
  border-radius: 6px;
  color: #f4f4fb;
  padding: 8px 14px;
}
QPushButton#Primary {
  background: #5f55d8;
  border-color: #8d83ff;
  font-weight: 700;
}
QPushButton:disabled {
  color: #777b8c;
  background: #353535;
}
"""


class ChordGeneratorDialog(QDialog):
    def __init__(self, parent: Any = None, initial_text: str = "") -> None:
        super().__init__(parent)
        self.setWindowTitle("Guitarist Chord Generator")
        self.resize(760, 520)
        self.setStyleSheet(STYLE_SHEET)

        layout = QVBoxLayout()
        self.setLayout(layout)

        title = QLabel("Guitar Chord Anki Generator")
        title.setObjectName("Title")
        subtitle = QLabel("Create clean chord cards with diagrams and audio.")
        subtitle.setObjectName("Subtitle")
        layout.addWidget(title)
        layout.addWidget(subtitle)

        tabs = QTabWidget()
        layout.addWidget(tabs)

        generator_tab = QWidget()
        generator_layout = QHBoxLayout()
        generator_tab.setLayout(generator_layout)
        tabs.addTab(generator_tab, "Generator")

        controls = QFrame()
        controls.setObjectName("Card")
        controls_layout = QVBoxLayout()
        controls.setLayout(controls_layout)
        generator_layout.addWidget(controls, 3)

        controls_layout.addWidget(QLabel("Chord names"))
        self.input = QPlainTextEdit()
        self.input.setPlaceholderText("C, Am, G7, Dm7")
        self.input.setPlainText(initial_text)
        self.input.setFixedHeight(92)
        controls_layout.addWidget(self.input)

        controls_layout.addWidget(QLabel("Suggestions"))
        self.suggestions = QListWidget()
        self.suggestions.setFixedHeight(104)
        controls_layout.addWidget(self.suggestions)

        self.summary = QLabel("")
        self.summary.setObjectName("Subtitle")
        controls_layout.addWidget(self.summary)

        controls_layout.addWidget(QLabel("Validation"))
        self.preview = QListWidget()
        controls_layout.addWidget(self.preview)

        preview_card = QFrame()
        preview_card.setObjectName("Card")
        preview_layout = QVBoxLayout()
        preview_card.setLayout(preview_layout)
        generator_layout.addWidget(preview_card, 2)

        preview_label = QLabel("Preview")
        preview_label.setObjectName("Subtitle")
        preview_layout.addWidget(preview_label)
        self.diagram_preview = ChordPreviewWidget()
        preview_layout.addWidget(self.diagram_preview)

        options_tab = QWidget()
        options_layout = QVBoxLayout()
        options_tab.setLayout(options_layout)
        tabs.addTab(options_tab, "Options")
        options_layout.addWidget(QLabel("Version 1 uses standard tuning, curated common voicings, finger numbers, and generated WAV audio."))
        options_layout.addStretch(1)

        about_tab = QWidget()
        about_layout = QVBoxLayout()
        about_tab.setLayout(about_layout)
        tabs.addTab(about_tab, "About")
        about_layout.addWidget(QLabel("Guitarist creates Anki chord notes in the Guitarist deck."))
        about_layout.addStretch(1)

        button_row = QHBoxLayout()
        button_row.addStretch(1)
        cancel_button = QPushButton("Cancel")
        self.create_button = QPushButton("Add Card")
        self.create_button.setObjectName("Primary")
        button_row.addWidget(cancel_button)
        button_row.addWidget(self.create_button)
        layout.addLayout(button_row)

        qconnect(self.input.textChanged, self.refresh_preview)
        qconnect(self.input.cursorPositionChanged, self.refresh_suggestions)
        qconnect(self.suggestions.itemClicked, self.accept_suggestion)
        qconnect(self.suggestions.itemActivated, self.accept_suggestion)
        qconnect(self.create_button.clicked, self.create_notes)
        qconnect(cancel_button.clicked, self.reject)

        self.refresh_preview()

    def _current_token_bounds(self) -> tuple[int, int, str]:
        text = self.input.toPlainText()
        cursor_position = self.input.textCursor().position()
        start = cursor_position
        while start > 0 and text[start - 1] not in ",;\n":
            start -= 1
        end = cursor_position
        while end < len(text) and text[end] not in ",;\n":
            end += 1

        token_start = start
        while token_start < end and text[token_start].isspace():
            token_start += 1
        token_end = end
        while token_end > token_start and text[token_end - 1].isspace():
            token_end -= 1
        return token_start, token_end, text[token_start:token_end]

    def refresh_suggestions(self) -> None:
        self.suggestions.clear()
        _, _, token = self._current_token_bounds()
        if not token.strip():
            return

        for suggestion in suggest_chords(token):
            item = QListWidgetItem(f"{suggestion.chord}    {suggestion.voicing_name}")
            item.setData(_user_role(), suggestion.chord)
            self.suggestions.addItem(item)

    def accept_suggestion(self, item: QListWidgetItem) -> None:
        chord = item.data(_user_role())
        if not chord:
            return

        start, end, _ = self._current_token_bounds()
        cursor = self.input.textCursor()
        cursor.setPosition(start)
        cursor.setPosition(end, _keep_anchor())
        cursor.insertText(str(chord))
        self.input.setTextCursor(cursor)
        self.input.setFocus()
        self.refresh_preview()

    def refresh_preview(self) -> None:
        self.preview.clear()
        text = self.input.toPlainText()
        chord_inputs = parse_chord_inputs(text)
        self.summary.setText(f"{len(chord_inputs)} chord(s) queued" if chord_inputs else "No chords queued")
        self.create_button.setText("Add Card" if len(chord_inputs) <= 1 else "Add Cards")
        self.create_button.setEnabled(bool(chord_inputs))

        for line in preview_inputs(text):
            self.preview.addItem(line)
        self.refresh_suggestions()
        if not chord_inputs:
            self.diagram_preview.set_voicing(None)
            return

        try:
            self.diagram_preview.set_voicing(lookup_voicing(chord_inputs[0]))
        except Exception:
            self.diagram_preview.set_voicing(None)

    def create_notes(self) -> None:
        text = self.input.toPlainText().strip()
        if not parse_chord_inputs(text):
            showWarning("Enter at least one chord name.")
            return

        self.create_button.setEnabled(False)

        def on_success(result: AddChordsResult) -> None:
            created_count = len(result.created)
            skipped_count = len(result.unsupported)
            if created_count:
                tooltip(f"Created {created_count} Guitarist chord note(s).")
            if skipped_count:
                skipped: List[str] = [
                    f"{item.requested}: {item.reason}" for item in result.unsupported
                ]
                showInfo("Skipped unsupported chords:\n\n" + "\n".join(skipped))
            self.accept()

        def on_failure(exc: Exception) -> None:
            self.create_button.setEnabled(True)
            showWarning(f"Could not create Guitarist notes:\n\n{exc}")

        CollectionOp(
            parent=self,
            op=lambda col: add_chord_notes(col, text),
        ).success(on_success).failure(on_failure).run_in_background(initiator=self)


def open_chord_generator(parent: Any = None, initial_text: str = "") -> None:
    dialog = ChordGeneratorDialog(parent or mw, initial_text=initial_text)
    if hasattr(dialog, "exec"):
        dialog.exec()
    else:
        dialog.exec_()


def _on_tools_action() -> None:
    open_chord_generator(mw)


def _on_editor_button(editor: Any) -> None:
    open_chord_generator(getattr(editor, "parentWindow", mw))


def _add_editor_button(buttons: List[str], editor: Any) -> None:
    if hasattr(editor, "addButton"):
        kwargs = dict(
            icon=None,
            cmd="guitarist_chord_generator",
            func=_on_editor_button,
            tip="Create guitar chord notes",
            label="Gtr",
            id="guitarist-chord-generator",
        )
        try:
            button = editor.addButton(**kwargs)
        except TypeError:
            kwargs.pop("id", None)
            button = editor.addButton(**kwargs)
        buttons.append(button)
        return

    editor._links["guitarist_chord_generator"] = _on_editor_button
    buttons.append(
        editor._addButton(
            None,
            "guitarist_chord_generator",
            "Create guitar chord notes",
        )
    )


def _refresh_existing_cards(*args: Any) -> None:
    if getattr(mw, "col", None) is None:
        return
    try:
        CollectionOp(parent=mw, op=lambda col: refresh_existing_notetype(col)).run_in_background(
            initiator=mw
        )
    except Exception:
        pass


_REGISTERED = False


def register_hooks() -> None:
    global _REGISTERED
    if _REGISTERED:
        return

    action = QAction("Guitarist Chord Generator", mw)
    qconnect(action.triggered, _on_tools_action)
    mw.form.menuTools.addAction(action)

    gui_hooks.editor_did_init_buttons.append(_add_editor_button)
    profile_hook = getattr(gui_hooks, "profile_did_open", None)
    if profile_hook is not None:
        profile_hook.append(_refresh_existing_cards)
    _refresh_existing_cards()
    _REGISTERED = True
