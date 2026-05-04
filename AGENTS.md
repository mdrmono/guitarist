# Repository Guidelines

## Project Structure & Module Organization

This repository is an Anki add-on package. Anki loads root `__init__.py`, which
registers UI hooks from `ui/dialog.py`. Core logic lives under `core/`:
`chords.py` parses chord names and selects voicings, `diagram.py` renders SVG
fretboard diagrams, `audio.py` synthesizes WAV audio, `generator.py` prepares
chord assets, and `settings.py` validates add-on config. Anki collection work
lives in `integration/collection.py`, development-only helpers live in `dev/`, add-on
metadata and defaults live in `manifest.json`, `config.json`, and `config.md`,
and tests live under `tests/`.

## Build, Test, and Development Commands

- `python3 -m unittest`: run the full unit test suite.
- `python3 -m py_compile __init__.py core/*.py integration/*.py ui/*.py dev/*.py`: catch syntax/import-time issues in source files.
- `scripts/install_dev.sh`: install a copied development build into Anki.
- `anki --version`: confirm the local Anki executable and version.

Restart Anki after copying files into `addons21`.

## Coding Style & Naming Conventions

Use Python 3.9+ with 4-space indentation, type hints, and dataclasses for
structured values. Keep Anki-specific imports isolated to `ui/` and
`integration/` so core modules remain testable without Anki installed. Prefer small pure
functions in `core/chords.py`, `core/diagram.py`, `core/audio.py`, and
`core/generator.py`. Use `snake_case` for functions and variables,
`PascalCase` for classes, and uppercase constants for shared configuration.

## Testing Guidelines

Tests use the standard library `unittest` framework. Name files `tests/test_*.py` and test classes by behavior, for example `ChordParsingTests` or `MediaGenerationTests`. Cover chord parsing, voicing lookup, unsupported input handling, SVG output, and WAV validity. Add regression tests for every supported chord-quality expansion or Anki field/template change where possible.

## Commit & Pull Request Guidelines

Use Conventional Commits for all commit messages: `type(scope): summary`. Keep summaries imperative and under 72 characters, for example `feat(chords): add maj9 voicings`, `fix(ui): handle older editor hooks`, or `test(audio): cover wav headers`. Common types are `feat`, `fix`, `test`, `docs`, `refactor`, and `chore`.

Before pushing to GitHub, run tests and a secret scan:

- `python3 -m unittest`
- `gitleaks detect --source . --redact`

Do not push if `gitleaks` reports a finding. Remove the secret, rotate it if it
was real, and rerun the scan. Pull requests should include a short summary,
test results, screenshots for UI changes, and any manual Anki smoke-test notes.
Mention affected Anki versions when changing `ui/dialog.py` or
`integration/collection.py`.

## GitHub Workflow

The remote is `origin` at `https://github.com/mdrmono/guitarist.git`. Work on topic branches named by purpose, such as `feat/chord-options` or `fix/audio-playback`. Keep PRs focused, avoid committing generated caches, and ensure copied Anki install files are not treated as the source of truth.

## Agent-Specific Instructions

Do not edit installed copies in `~/.local/share/Anki2/addons21/guitarist` as the source of truth. Make changes in this repository, run tests, then copy/install the add-on.
