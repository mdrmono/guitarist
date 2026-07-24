# Guitarist Configuration

- `deckName`: destination deck for generated chord notes.
- `noteTypeName`: managed note type name. Guitarist creates or updates this note
  type's fields, card templates, and styling.
- `clearInputAfterAdd`: clear the chord input after successful note creation.
- `keepUnsupportedAfterAdd`: keep unsupported chord names in the input box.
- `sampleBankPath`: optional absolute path to an external WAV sample bank. Files
  must be mono or multichannel 16-bit PCM at 44.1 kHz and use scientific pitch
  filenames such as `E2.wav`, `Cs4.wav`, and `As4.wav`. Leave blank to use the
  built-in physical-model guitar synthesizer.
- `strumSpeed`: primary strum speed for new cards: `Fast`, `Medium`, or `Slow`.
  Every new card also includes a fixed note-by-note study strum.
