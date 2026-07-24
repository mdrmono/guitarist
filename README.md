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
- Offline physical-model WAV synthesis for realistic strummed chord audio.
- Optional external 44.1 kHz WAV sample banks for recorded strummed chord audio.
- Selectable primary strum speed plus a separate note-by-note slow recording.
- Speed-specific custom playback icons on generated Anki cards.
- Configurable destination deck and managed `Guitarist Chord` note type.

## Supported Chords

Major, minor, dominant seventh, major seventh, minor seventh, suspended fourth,
and power chords are supported with common open voicings and movable E/A-shape
voicings.

Examples:

```text
C, Am, F#, Bb7, Gmaj7, Dsus4
```

## Installation

Guitarist has been tested with Anki 24.06.2.

1. Download the `.ankiaddon` file from the
   [latest GitHub release](https://github.com/mdrmono/guitarist/releases/latest).
2. Open the downloaded file with Anki and confirm the installation.
3. Restart Anki, then select **Tools > Guitarist Chord Generator**.

Enter one chord or paste a comma- or line-separated batch, preview the generated
voicings, and choose **Add Card**. The Options tab lets you select the destination
deck and control what happens to the input after notes are created. Advanced
defaults, including the managed note type name, are documented in `config.md`.
External recordings are not bundled; configure `sampleBankPath` to use a local
sample bank and leave it blank to use Guitarist's built-in synthesizer.

## Repository Layout

```text
__init__.py          Anki add-on entry point
core/                Parsing, voicing lookup, rendering, audio, settings
assets/icons/        Vector playback icons copied into Anki collection media
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

Build the distributable add-on package:

```bash
scripts/build_addon.sh
```

The package is written to `dist/` with its version read from `pyproject.toml`.

For faster Python-only iteration, start Anki with the development reload action:

```bash
GUITARIST_DEV_RELOAD=1 anki
```

This adds Tools > Reload Guitarist Add-on, which reloads the add-on modules and
opens a fresh generator dialog. Restart Anki for hook registration, startup, or
already-constructed Qt widget changes that do not refresh cleanly.

## License

Guitarist is available under the [MIT License](LICENSE).
