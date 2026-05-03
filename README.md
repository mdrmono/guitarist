# Guitarist

Guitarist is an Anki add-on for generating guitar chord study notes. Version 1
lets a user type chord names, then creates Anki notes with a fretboard diagram,
synthesized chord audio, and two review cards.

## Features

- Tools menu chord generator dialog.
- Editor toolbar entry point.
- Built-in common chord voicings for standard tuning.
- Offline SVG fretboard diagrams.
- Offline WAV synthesis for strummed chord audio.
- Configurable destination deck and managed `Guitarist Chord` note type.

## Supported v1 chord types

Major, minor, dominant seventh, major seventh, minor seventh, suspended fourth,
and power chords are supported with common open voicings and movable E/A-shape
voicings.

Examples:

```text
C, Am, F#, Bb7, Gmaj7, Dsus4
```

## Local development

Run the core tests:

```bash
python3 -m unittest
```

To test in Anki, copy a development build into Anki's `addons21` directory:

```bash
rsync -a --delete \
  --exclude .git \
  --exclude __pycache__ \
  --exclude tests \
  ./ ~/.local/share/Anki2/addons21/guitarist/
```

Restart Anki after copying the files.

For faster Python-only iteration, start Anki with a development reload action:

```bash
GUITARIST_DEV_RELOAD=1 anki
```

This adds Tools > Reload Guitarist Add-on, which reloads the add-on modules and
opens a fresh generator dialog. Restart Anki for hook registration, startup, or
already-constructed Qt widget changes that do not refresh cleanly.
