"""SVG fretboard diagram rendering."""

from __future__ import annotations

import html
from typing import List, Optional

from .chords import Voicing


def _display_base_fret(voicing: Voicing) -> int:
    fretted = [fret for fret in voicing.positions if fret is not None and fret > 0]
    if not fretted:
        return 1
    if max(fretted) <= 4:
        return 1
    return min(fretted)


def _svg_text(
    x: float,
    y: float,
    text: str,
    size: int = 18,
    weight: str = "500",
    fill: str = "#f4f4fb",
) -> str:
    return (
        f'<text x="{x:.1f}" y="{y:.1f}" text-anchor="middle" '
        f'font-family="Arial, Helvetica, sans-serif" font-size="{size}" '
        f'font-weight="{weight}" fill="{fill}">{html.escape(text)}</text>'
    )


def render_chord_svg(voicing: Voicing) -> str:
    width = 360
    height = 360
    left = 58
    top = 46
    string_gap = 44
    fret_gap = 48
    fret_count = 5
    base_fret = _display_base_fret(voicing)
    right = left + string_gap * 5
    bottom = top + fret_gap * fret_count
    label = html.escape(voicing.chord)

    parts: List[str] = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" '
        f'viewBox="0 0 {width} {height}" role="img" aria-label="{label} guitar chord diagram" '
        f'data-chord="{label}" data-voicing="{html.escape(voicing.name)}">',
        '<rect width="100%" height="100%" fill="transparent"/>',
    ]

    for string_idx in range(6):
        x = left + string_gap * string_idx
        stroke_width = 2.7 - min(string_idx, 4) * 0.18
        parts.append(
            f'<line x1="{x:.1f}" y1="{top:.1f}" x2="{x:.1f}" y2="{bottom:.1f}" '
            f'stroke="#f4f4fb" stroke-width="{stroke_width:.2f}" stroke-linecap="round" opacity="0.96"/>'
        )

    for fret_idx in range(fret_count + 1):
        y = top + fret_gap * fret_idx
        stroke_width = 5.5 if fret_idx == 0 and base_fret == 1 else 2.0
        parts.append(
            f'<line x1="{left:.1f}" y1="{y:.1f}" x2="{right:.1f}" y2="{y:.1f}" '
            f'stroke="#f4f4fb" stroke-width="{stroke_width:.1f}" stroke-linecap="round" opacity="0.92"/>'
        )

    if base_fret > 1:
        parts.append(_svg_text(left - 30, top + fret_gap / 2 + 6, str(base_fret), 16, "700"))
        parts.append(_svg_text(left - 30, top + fret_gap / 2 + 24, "fr", 10, "400", "#a7a1ff"))

    for string_idx, string_name in enumerate(voicing.string_note_names):
        x = left + string_gap * string_idx
        fret = voicing.positions[string_idx]
        top_marker = "x" if fret is None else "o" if fret == 0 else ""
        if top_marker:
            parts.append(_svg_text(x, top - 22, top_marker, 20, "700"))
        if string_name:
            parts.append(_svg_text(x, bottom + 28, string_name, 12, "500", "#f4f4fb"))

    for string_idx, fret in enumerate(voicing.positions):
        if fret is None or fret == 0:
            continue
        relative_fret = fret - base_fret + 1
        if relative_fret < 1 or relative_fret > fret_count:
            continue
        x = left + string_gap * string_idx
        y = top + fret_gap * (relative_fret - 0.5)
        parts.append(f'<circle cx="{x:.1f}" cy="{y:.1f}" r="17" fill="#6457d7"/>')
        parts.append(f'<circle cx="{x - 5:.1f}" cy="{y - 6:.1f}" r="5" fill="#958cff" opacity="0.75"/>')
        finger: Optional[int] = voicing.fingers[string_idx]
        if finger is not None:
            parts.append(
                f'<text x="{x:.1f}" y="{y + 6:.1f}" text-anchor="middle" '
                'font-family="Arial, Helvetica, sans-serif" font-size="16" '
                'font-weight="700" fill="#ffffff">'
                f"{finger}</text>"
            )

    parts.append(_svg_text(width / 2, height - 24, voicing.fingering_text, 14, "500", "#f4f4fb"))
    parts.append("</svg>")
    return "\n".join(parts)
