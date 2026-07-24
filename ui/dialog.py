"""Qt dialog and Anki UI hooks for the Guitarist add-on."""

from __future__ import annotations

from typing import Any, List, Optional

from aqt import gui_hooks, mw  # type: ignore
from aqt.operations import CollectionOp  # type: ignore
from aqt.qt import (  # type: ignore
    QAction,
    QBrush,
    QCheckBox,
    QColor,
    QComboBox,
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
    QSizePolicy,
    QTabWidget,
    QTextCursor,
    Qt,
    QVBoxLayout,
    QWidget,
)
from aqt.utils import qconnect, showInfo, showWarning, tooltip  # type: ignore

from ..integration.collection import (
    AddChordsResult,
    add_chord_notes,
    preview_inputs,
    refresh_existing_notetype,
)
from ..core.chords import Voicing, lookup_voicing, parse_chord_inputs, suggest_chords
from ..core.settings import (
    DEFAULT_STRUM_SPEED,
    STRUM_SPEED_DELAYS,
    GuitaristSettings,
    apply_settings_to_config,
    settings_from_config,
)
from ..dev.reload import dev_reload_enabled, reload_addon_modules


ADDON_REPO_URL = "https://github.com/mdrmono/guitarist"
ADDON_PACKAGE = __name__.split(".", 1)[0]


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


def _size_policy(name: str) -> Any:
    policy = getattr(QSizePolicy, "Policy", QSizePolicy)
    return getattr(policy, name)


class ChordPreviewWidget(QWidget):
    def __init__(self, parent: Any = None, empty_text: str = "Type a chord") -> None:
        super().__init__(parent)
        self._voicing: Optional[Voicing] = None
        self._empty_text = empty_text
        self.setMinimumSize(240, 288)
        self.setSizePolicy(_size_policy("Expanding"), _size_policy("Expanding"))

    def set_voicing(self, voicing: Optional[Voicing]) -> None:
        self._voicing = voicing
        self.update()

    def set_empty_text(self, text: str) -> None:
        self._empty_text = text
        if self._voicing is None:
            self.update()

    def paintEvent(self, event: Any) -> None:
        painter = QPainter(self)
        painter.setRenderHint(_antialiasing())
        painter.fillRect(self.rect(), QColor("#2b2b2b"))

        panel = QRectF(1, 1, self.width() - 2, self.height() - 2)
        painter.setPen(QPen(QColor("#3a3d4b"), 1))
        painter.setBrush(QBrush(QColor("#f4f1ec")))
        painter.drawRoundedRect(panel, 8, 8)

        if self._voicing is None:
            painter.setPen(QColor("#6a6f82"))
            painter.setFont(QFont("Arial", 13))
            painter.drawText(panel, _align_center(), self._empty_text)
            painter.end()
            return

        voicing = self._voicing
        painter.setPen(QColor("#0f1118"))
        title_font = QFont("Arial", 22)
        title_font.setBold(True)
        painter.setFont(title_font)
        painter.drawText(
            QRectF(panel.left(), panel.top() + 12, panel.width(), 36),
            _align_center(),
            voicing.chord,
        )

        horizontal_margin = max(28.0, min(42.0, panel.width() * 0.13))
        left = panel.left() + horizontal_margin
        right = panel.right() - horizontal_margin
        top = panel.top() + 72
        string_gap = (right - left) / 5
        available_grid_height = max(160.0, panel.bottom() - top - 44)
        fret_gap = max(32.0, min(50.0, available_grid_height / 5))
        bottom = top + fret_gap * 5
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
QLabel#OptionHelp,
QLabel#AboutText,
QLabel#OptionsStatus {
  color: #a9abba;
  font-size: 12px;
}
QFrame#Card {
  background: #303030;
  border: 1px solid #404040;
  border-radius: 8px;
}
QPlainTextEdit,
QListWidget,
QComboBox {
  background: #353535;
  border: 1px solid #474747;
  border-radius: 6px;
  color: #f4f4fb;
  selection-background-color: #544cc8;
  padding: 6px;
}
QCheckBox {
  color: #f4f4fb;
  spacing: 8px;
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
QPushButton#PreviewNav {
  font-size: 16px;
  font-weight: 700;
  min-width: 34px;
  padding: 4px 8px;
}
QPushButton:disabled {
  color: #777b8c;
  background: #353535;
}
QLabel#PreviewCounter {
  color: #d9d8e8;
  font-size: 12px;
}
"""


def _load_addon_settings() -> GuitaristSettings:
    try:
        config = mw.addonManager.getConfig(ADDON_PACKAGE)
    except Exception:
        config = None
    return settings_from_config(config)


def _write_addon_settings(settings: GuitaristSettings) -> None:
    config = mw.addonManager.getConfig(ADDON_PACKAGE)
    updated = apply_settings_to_config(config, settings)
    mw.addonManager.writeConfig(ADDON_PACKAGE, updated)


def _deck_names() -> List[str]:
    col = getattr(mw, "col", None)
    if col is None:
        return []

    decks = col.decks
    try:
        if hasattr(decks, "all_names_and_ids"):
            return sorted(deck.name for deck in decks.all_names_and_ids())
        if hasattr(decks, "all_names"):
            return sorted(decks.all_names())
        if hasattr(decks, "allNames"):
            return sorted(decks.allNames())
    except Exception:
        return []
    return []


class ChordGeneratorDialog(QDialog):
    def __init__(self, parent: Any = None, initial_text: str = "") -> None:
        super().__init__(parent)
        self.setWindowTitle("Guitarist Chord Generator")
        self.resize(760, 520)
        self.setStyleSheet(STYLE_SHEET)
        self.settings = _load_addon_settings()
        self.preview_voicings: List[Voicing] = []
        self.preview_index = 0

        layout = QVBoxLayout()
        self.setLayout(layout)

        title = QLabel("Guitar Chord Anki Generator")
        title.setObjectName("Title")
        subtitle = QLabel("Type one chord or paste a comma/newline-separated batch.")
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
        self.input.setPlaceholderText("C, Am, G7\nDm7")
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
        preview_layout.setContentsMargins(4, 4, 4, 4)
        preview_layout.setSpacing(0)
        preview_card.setLayout(preview_layout)
        generator_layout.addWidget(preview_card, 2)

        self.diagram_preview = ChordPreviewWidget()
        preview_layout.addWidget(self.diagram_preview, 1)

        self.preview_nav = QWidget()
        preview_nav_layout = QHBoxLayout()
        preview_nav_layout.setContentsMargins(0, 4, 0, 0)
        preview_nav_layout.setSpacing(8)
        self.preview_nav.setLayout(preview_nav_layout)
        self.previous_preview_button = QPushButton("<")
        self.previous_preview_button.setObjectName("PreviewNav")
        self.next_preview_button = QPushButton(">")
        self.next_preview_button.setObjectName("PreviewNav")
        self.preview_counter = QLabel("")
        self.preview_counter.setObjectName("PreviewCounter")
        preview_nav_layout.addWidget(self.previous_preview_button)
        preview_nav_layout.addStretch(1)
        preview_nav_layout.addWidget(self.preview_counter)
        preview_nav_layout.addStretch(1)
        preview_nav_layout.addWidget(self.next_preview_button)
        preview_layout.addWidget(self.preview_nav)

        options_tab = QWidget()
        options_layout = QVBoxLayout()
        options_layout.setContentsMargins(16, 14, 16, 14)
        options_layout.setSpacing(12)
        options_tab.setLayout(options_layout)
        tabs.addTab(options_tab, "Options")

        options_layout.addWidget(QLabel("Destination deck"))
        self.deck_selector = QComboBox()
        self.deck_selector.setEditable(True)
        self._populate_deck_selector()
        options_layout.addWidget(self.deck_selector)

        deck_help = QLabel("Type a new deck name to create it when cards are added.")
        deck_help.setObjectName("OptionHelp")
        deck_help.setWordWrap(True)
        options_layout.addWidget(deck_help)

        options_layout.addWidget(QLabel("Primary strumming speed"))
        self.strum_speed_selector = QComboBox()
        for speed in STRUM_SPEED_DELAYS:
            self.strum_speed_selector.addItem(speed, speed)
        selected_speed_index = self.strum_speed_selector.findData(
            self.settings.strum_speed
        )
        if selected_speed_index < 0:
            selected_speed_index = self.strum_speed_selector.findData(
                DEFAULT_STRUM_SPEED
            )
        self.strum_speed_selector.setCurrentIndex(selected_speed_index)
        options_layout.addWidget(self.strum_speed_selector)

        speed_help = QLabel(
            "Each new card also receives a separate note-by-note slow strum "
            "at 500 ms between strings."
        )
        speed_help.setObjectName("OptionHelp")
        speed_help.setWordWrap(True)
        options_layout.addWidget(speed_help)

        self.clear_input_checkbox = QCheckBox("Clear chord input after adding cards")
        self.clear_input_checkbox.setChecked(self.settings.clear_input_after_add)
        options_layout.addWidget(self.clear_input_checkbox)

        self.keep_unsupported_checkbox = QCheckBox("Keep unsupported chords in input")
        self.keep_unsupported_checkbox.setChecked(self.settings.keep_unsupported_after_add)
        options_layout.addWidget(self.keep_unsupported_checkbox)

        save_options_button = QPushButton("Save Options")
        save_options_button.setObjectName("Primary")
        options_layout.addWidget(save_options_button)

        self.options_status = QLabel("")
        self.options_status.setObjectName("OptionsStatus")
        options_layout.addWidget(self.options_status)
        options_layout.addStretch(1)

        about_tab = QWidget()
        about_layout = QVBoxLayout()
        about_layout.setContentsMargins(16, 14, 16, 14)
        about_layout.setSpacing(10)
        about_tab.setLayout(about_layout)
        tabs.addTab(about_tab, "About")
        about_text = QLabel(
            "Guitarist is an Anki add-on for creating guitar chord study cards "
            "with fretboard diagrams, fingerings, and generated strum audio."
        )
        about_text.setObjectName("AboutText")
        about_text.setWordWrap(True)
        about_layout.addWidget(about_text)

        repo_label = QLabel(
            f'Repository: <a href="{ADDON_REPO_URL}">{ADDON_REPO_URL}</a>'
        )
        repo_label.setObjectName("AboutText")
        repo_label.setOpenExternalLinks(True)
        repo_label.setWordWrap(True)
        about_layout.addWidget(repo_label)
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
        qconnect(self.previous_preview_button.clicked, self.show_previous_preview)
        qconnect(self.next_preview_button.clicked, self.show_next_preview)
        qconnect(save_options_button.clicked, self.save_options)

        self.refresh_preview()

    def _populate_deck_selector(self) -> None:
        seen = set()
        for deck_name in [self.settings.deck_name] + _deck_names():
            if deck_name in seen:
                continue
            self.deck_selector.addItem(deck_name)
            seen.add(deck_name)

    def current_options_settings(self) -> GuitaristSettings:
        return GuitaristSettings(
            deck_name=self.deck_selector.currentText().strip(),
            note_type_name=self.settings.note_type_name,
            clear_input_after_add=self.clear_input_checkbox.isChecked(),
            keep_unsupported_after_add=self.keep_unsupported_checkbox.isChecked(),
            sample_bank_path=self.settings.sample_bank_path,
            strum_speed=str(
                self.strum_speed_selector.currentData() or DEFAULT_STRUM_SPEED
            ),
        )

    def save_options(self) -> bool:
        settings = self.current_options_settings()
        if not settings.deck_name:
            showWarning("Choose a destination deck.")
            return False
        try:
            _write_addon_settings(settings)
        except Exception as exc:
            showWarning(f"Could not save Guitarist options:\n\n{exc}")
            return False

        self.settings = settings
        self.options_status.setText(f"Saved. New cards will go to {settings.deck_name}.")
        tooltip("Saved Guitarist options.")
        return True

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
        self.summary.setText(
            f"{len(chord_inputs)} chord(s) queued" if chord_inputs else "No chords queued"
        )
        self.create_button.setText("Add Card" if len(chord_inputs) <= 1 else "Add Cards")
        self.create_button.setEnabled(bool(chord_inputs))

        for line in preview_inputs(text):
            self.preview.addItem(line)
        self.refresh_suggestions()
        self.refresh_diagram_previews(chord_inputs)

    def refresh_diagram_previews(self, chord_inputs: List[str]) -> None:
        current_chord = None
        if self.preview_voicings:
            current_chord = self.preview_voicings[self.preview_index].chord

        if not chord_inputs:
            self.preview_voicings = []
            self.preview_index = 0
            self.diagram_preview.set_empty_text("Type a chord")
            self.diagram_preview.set_voicing(None)
            self.refresh_preview_navigation()
            return

        self.preview_voicings = []
        for requested in chord_inputs:
            try:
                voicing = lookup_voicing(requested)
            except Exception:
                continue
            self.preview_voicings.append(voicing)

        if not self.preview_voicings:
            self.preview_index = 0
            self.diagram_preview.set_empty_text("No supported chords")
            self.diagram_preview.set_voicing(None)
            self.refresh_preview_navigation()
            return

        if current_chord:
            chords = [voicing.chord for voicing in self.preview_voicings]
            if current_chord in chords:
                self.preview_index = chords.index(current_chord)
            else:
                self.preview_index = min(self.preview_index, len(self.preview_voicings) - 1)
        else:
            self.preview_index = 0
        self.show_current_preview()

    def show_current_preview(self) -> None:
        if not self.preview_voicings:
            self.refresh_preview_navigation()
            return
        self.diagram_preview.set_voicing(self.preview_voicings[self.preview_index])
        self.refresh_preview_navigation()

    def refresh_preview_navigation(self) -> None:
        preview_count = len(self.preview_voicings)
        show_navigation = preview_count > 1
        self.preview_nav.setVisible(show_navigation)
        self.previous_preview_button.setEnabled(self.preview_index > 0)
        self.next_preview_button.setEnabled(self.preview_index < preview_count - 1)
        if show_navigation:
            self.preview_counter.setText(f"{self.preview_index + 1} / {preview_count}")
        else:
            self.preview_counter.setText("")

    def show_previous_preview(self) -> None:
        if self.preview_index <= 0:
            return
        self.preview_index -= 1
        self.show_current_preview()

    def show_next_preview(self) -> None:
        if self.preview_index >= len(self.preview_voicings) - 1:
            return
        self.preview_index += 1
        self.show_current_preview()

    def create_notes(self) -> None:
        text = self.input.toPlainText().strip()
        if not parse_chord_inputs(text):
            showWarning("Enter at least one chord name.")
            return
        settings = self.current_options_settings()
        if not settings.deck_name:
            showWarning("Choose a destination deck.")
            return
        try:
            _write_addon_settings(settings)
            self.settings = settings
        except Exception:
            pass

        self.create_button.setEnabled(False)

        def on_success(result: AddChordsResult) -> None:
            self.create_button.setEnabled(True)
            created_count = len(result.created)
            skipped_count = len(result.unsupported)
            if created_count:
                tooltip(f"Created {created_count} Guitarist chord note(s).")
            if skipped_count:
                skipped: List[str] = [
                    f"{item.requested}: {item.reason}" for item in result.unsupported
                ]
                showInfo("Skipped unsupported chords:\n\n" + "\n".join(skipped))
                if settings.keep_unsupported_after_add:
                    self.input.setPlainText(
                        ", ".join(item.requested for item in result.unsupported)
                    )
                elif settings.clear_input_after_add:
                    self.input.clear()
            elif created_count and settings.clear_input_after_add:
                self.input.clear()
            self.input.setFocus()
            self.refresh_preview()

        def on_failure(exc: Exception) -> None:
            self.create_button.setEnabled(True)
            showWarning(f"Could not create Guitarist notes:\n\n{exc}")

        CollectionOp(
            parent=self,
            op=lambda col: add_chord_notes(
                col,
                text,
                deck_name=settings.deck_name,
                note_type_name=settings.note_type_name,
                sample_bank_path=settings.sample_bank_path,
                strum_speed=settings.strum_speed,
            ),
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


def _on_dev_reload_action() -> None:
    try:
        reloaded = reload_addon_modules()
    except Exception as exc:
        showWarning(f"Could not reload Guitarist modules:\n\n{exc}")
        return

    tooltip(f"Reloaded {len(reloaded)} Guitarist module(s).")
    open_chord_generator(mw)


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
        settings = _load_addon_settings()
        CollectionOp(
            parent=mw,
            op=lambda col: refresh_existing_notetype(col, settings.note_type_name),
        ).run_in_background(initiator=mw)
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

    if dev_reload_enabled():
        reload_action = QAction("Reload Guitarist Add-on", mw)
        qconnect(reload_action.triggered, _on_dev_reload_action)
        mw.form.menuTools.addAction(reload_action)

    gui_hooks.editor_did_init_buttons.append(_add_editor_button)
    profile_hook = getattr(gui_hooks, "profile_did_open", None)
    if profile_hook is not None:
        profile_hook.append(_refresh_existing_cards)
    _refresh_existing_cards()
    _REGISTERED = True
