"""Anki collection integration for generated chord notes."""

from __future__ import annotations

import html
from dataclasses import dataclass
from typing import Any, List, Sequence, Tuple

from .chords import UnsupportedChord, lookup_voicing, parse_chord_inputs
from .generator import ChordAsset, UnsupportedInput, prepare_generation
from .settings import DEFAULT_DECK_NAME, DEFAULT_NOTE_TYPE_NAME


DECK_NAME = DEFAULT_DECK_NAME
NOTE_TYPE_NAME = DEFAULT_NOTE_TYPE_NAME
FIELDS = ("Chord", "Voicing", "Diagram", "Audio", "Fingering", "Notes")

CARD_TEMPLATES = (
    (
        "Identify Chord",
        """
<div class="guitarist-shell">
  <div class="prompt">What chord is this?</div>
  <div class="diagram">{{Diagram}}</div>
</div>
""".strip(),
        """
{{FrontSide}}
<div class="answer-panel">
  <div class="answer chord-name">{{Chord}}</div>
  <div class="meta">{{Voicing}}</div>
  <div class="meta">Fingering: {{Fingering}}</div>
  <div class="audio">{{Audio}}</div>
</div>
""".strip(),
    ),
    (
        "Play/Recall Shape",
        """
<div class="guitarist-shell">
  <div class="prompt">Recall this chord shape</div>
  <div class="chord-name">{{Chord}}</div>
</div>
""".strip(),
        """
{{FrontSide}}
<div class="answer-panel">
  <div class="diagram">{{Diagram}}</div>
  <div class="meta">{{Voicing}}</div>
  <div class="meta">Fingering: {{Fingering}}</div>
  <div class="meta">Notes: {{Notes}}</div>
  <div class="audio">{{Audio}}</div>
</div>
""".strip(),
    ),
)

CARD_CSS = """
.card {
  background: #2b2b2b;
  color: #f4f4fb;
  font-family: Arial, Helvetica, sans-serif;
  font-size: 20px;
  text-align: center;
  letter-spacing: 0;
}
.guitarist-shell {
  display: grid;
  gap: 18px;
  justify-items: center;
  margin: 0 auto;
  max-width: 760px;
  padding: 28px 20px 18px;
}
.prompt {
  color: #f4f4fb;
  font-size: 28px;
  font-weight: 700;
  letter-spacing: 0;
}
.chord-name {
  color: #f4f4fb;
  font-size: 36px;
  font-weight: 700;
  line-height: 1.1;
}
.diagram img {
  height: auto;
  max-width: min(82vw, 300px);
}
.answer-panel {
  border-top: 1px solid rgba(244, 244, 251, 0.42);
  display: grid;
  gap: 10px;
  justify-items: center;
  margin: 22px auto 0;
  max-width: 760px;
  padding: 18px 20px 0;
}
.meta {
  color: #a7a1ff;
  font-size: 15px;
  line-height: 1.35;
}
.audio {
  margin-top: 8px;
}
""".strip()


@dataclass
class CreatedChordNote:
    chord: str
    diagram_filename: str
    audio_filename: str


@dataclass
class AddChordsResult:
    created: List[CreatedChordNote]
    unsupported: List[UnsupportedInput]
    changes: Any


def _empty_changes() -> Any:
    from anki.collection import OpChanges  # type: ignore

    return OpChanges()


def _extract_changes(result: Any) -> Any:
    return getattr(result, "changes", result)


def ensure_deck(col: Any, deck_name: str = DECK_NAME) -> Any:
    return col.decks.id(deck_name.strip() or DECK_NAME)


def ensure_notetype(col: Any) -> Tuple[Any, Any]:
    models = col.models
    notetype = models.by_name(NOTE_TYPE_NAME)
    changes = None

    if notetype is None:
        notetype = models.new(NOTE_TYPE_NAME)
        notetype["css"] = CARD_CSS
        notetype["sortf"] = 0
        for field_name in FIELDS:
            models.add_field(notetype, models.new_field(field_name))
        for template_name, qfmt, afmt in CARD_TEMPLATES:
            template = models.new_template(template_name)
            template["qfmt"] = qfmt
            template["afmt"] = afmt
            models.add_template(notetype, template)
        changes = _extract_changes(models.add(notetype))
        refreshed = models.by_name(NOTE_TYPE_NAME)
        return refreshed or notetype, changes

    changed = False
    existing_fields = set(models.field_names(notetype))
    for field_name in FIELDS:
        if field_name not in existing_fields:
            models.add_field(notetype, models.new_field(field_name))
            changed = True

    template_by_name = {template["name"]: template for template in notetype["tmpls"]}
    for template_name, qfmt, afmt in CARD_TEMPLATES:
        template = template_by_name.get(template_name)
        if template is None:
            template = models.new_template(template_name)
            template["qfmt"] = qfmt
            template["afmt"] = afmt
            models.add_template(notetype, template)
            changed = True
        elif template.get("qfmt") != qfmt or template.get("afmt") != afmt:
            template["qfmt"] = qfmt
            template["afmt"] = afmt
            changed = True

    if notetype.get("css") != CARD_CSS:
        notetype["css"] = CARD_CSS
        changed = True

    if changed:
        if hasattr(models, "update_dict"):
            changes = _extract_changes(models.update_dict(notetype))
        else:
            changes = _extract_changes(models.save(notetype))
        refreshed = models.by_name(NOTE_TYPE_NAME)
        return refreshed or notetype, changes

    return notetype, changes


def refresh_existing_notetype(col: Any) -> Any:
    models = col.models
    notetype = models.by_name(NOTE_TYPE_NAME)
    if notetype is None:
        return _empty_changes()

    changed = False
    template_by_name = {template["name"]: template for template in notetype["tmpls"]}
    for template_name, qfmt, afmt in CARD_TEMPLATES:
        template = template_by_name.get(template_name)
        if template is None:
            template = models.new_template(template_name)
            template["qfmt"] = qfmt
            template["afmt"] = afmt
            models.add_template(notetype, template)
            changed = True
        elif template.get("qfmt") != qfmt or template.get("afmt") != afmt:
            template["qfmt"] = qfmt
            template["afmt"] = afmt
            changed = True

    if notetype.get("css") != CARD_CSS:
        notetype["css"] = CARD_CSS
        changed = True

    if not changed:
        return _empty_changes()
    if hasattr(models, "update_dict"):
        return _extract_changes(models.update_dict(notetype))
    return _extract_changes(models.save(notetype))


def _media_image_tag(filename: str) -> str:
    return f'<img src="{html.escape(filename, quote=True)}">'


def _media_sound_tag(filename: str) -> str:
    return f"[sound:{filename}]"


def _write_asset_media(col: Any, asset: ChordAsset) -> Tuple[str, str]:
    diagram_name = col.media.write_data(asset.diagram_filename, asset.diagram_svg.encode("utf-8"))
    audio_name = col.media.write_data(asset.audio_filename, asset.audio_wav)
    return diagram_name, audio_name


def add_chord_notes(
    col: Any,
    input_text: str,
    deck_name: str = DECK_NAME,
) -> AddChordsResult:
    prepared = prepare_generation(input_text)
    changes = None

    if prepared.assets:
        deck_id = ensure_deck(col, deck_name)
        notetype, model_changes = ensure_notetype(col)
        changes = model_changes
    else:
        deck_id = None
        notetype = None

    created: List[CreatedChordNote] = []
    for asset in prepared.assets:
        diagram_name, audio_name = _write_asset_media(col, asset)
        note = col.new_note(notetype)
        _apply_asset_to_note(note, asset, diagram_name, audio_name)
        changes = _extract_changes(col.add_note(note, deck_id))
        created.append(
            CreatedChordNote(
                chord=asset.voicing.chord,
                diagram_filename=diagram_name,
                audio_filename=audio_name,
            )
        )

    return AddChordsResult(
        created=created,
        unsupported=prepared.unsupported,
        changes=changes if changes is not None else _empty_changes(),
    )


def _apply_asset_to_note(note: Any, asset: ChordAsset, diagram_name: str, audio_name: str) -> None:
    note["Chord"] = asset.voicing.chord
    note["Voicing"] = asset.voicing.name
    note["Diagram"] = _media_image_tag(diagram_name)
    note["Audio"] = _media_sound_tag(audio_name)
    note["Fingering"] = asset.voicing.fingering_text
    note["Notes"] = ", ".join(asset.voicing.note_names)


def preview_inputs(input_text: str) -> Sequence[str]:
    lines: List[str] = []
    for requested in parse_chord_inputs(input_text):
        try:
            voicing = lookup_voicing(requested)
        except UnsupportedChord as exc:
            lines.append(f"{requested} -> unsupported: {exc}")
        else:
            lines.append(f"{requested} -> {voicing.chord} ({voicing.name})")
    return lines
