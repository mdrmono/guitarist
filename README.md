# Guitarist

Guitarist is an Anki add-on for generating guitar chord study notes. Type one
chord or paste a batch, then create Anki notes with fretboard diagrams,
fingerings, generated strum audio, and two review cards.

## Features

- Tools menu chord generator dialog.
- Editor toolbar entry point.
- Batch chord input with validation and preview navigation.
- Built-in common chord voicings for standard tuning.
- Offline SVG fretboard diagrams.
- Offline WAV synthesis for strummed chord audio.
- Configurable destination deck and managed `Guitarist Chord` note type.

## Supported Chords

Major, minor, dominant seventh, major seventh, minor seventh, suspended fourth,
and power chords are supported with common open voicings and movable E/A-shape
voicings.

Examples:

```text
C, Am, F#, Bb7, Gmaj7, Dsus4
```

## Repository Layout

```text
__init__.py          Anki add-on entry point
core/                Parsing, voicing lookup, rendering, audio, settings
integration/         Deck, note type, media, and note creation
ui/                  Qt dialog and Anki UI hooks
dev/                 Development-only reload helper
tests/               Unit tests
scripts/             Local development scripts
manifest.json        Anki add-on metadata
config.json          Default add-on configuration
config.md            Configuration help shown in Anki
```

## Development

Run the tests:

```bash
python3 -m unittest
```

Install the working tree into Anki:

```bash
scripts/install_dev.sh
```

Restart Anki after copying files into `addons21`.

For faster Python-only iteration, start Anki with the development reload action:

```bash
GUITARIST_DEV_RELOAD=1 anki
```

This adds Tools > Reload Guitarist Add-on, which reloads the add-on modules and
opens a fresh generator dialog. Restart Anki for hook registration, startup, or
already-constructed Qt widget changes that do not refresh cleanly.
