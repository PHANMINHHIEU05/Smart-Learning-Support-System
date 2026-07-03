# SLSS Vocabulary Lookup Firefox Extension

## Purpose

This extension captures a selected English word from Firefox and saves it into the personal Smart Learning vocabulary library. If Spring Boot is unavailable, it falls back to Firefox local extension storage.

## Local Setup

1. In Firefox, open `about:debugging#/runtime/this-firefox`.
2. Click `Load Temporary Add-on`.
3. Select `manifest.json` from this folder.
4. Refresh any webpage that was already open before the add-on was loaded.
5. Start Spring Boot at `http://localhost:8080` if you want saves to appear in the web Vocabulary page.
6. Select an English word and open the popup to lookup, listen, and save.

## Use

1. Select a word on any webpage.
2. Open the extension popup or use the context menu.
3. The popup auto-lookups the word and shows Vietnamese meaning, phonetic text, English definition, pronunciation audio, and saved learning status.
4. Click `Listen` beside the selected word to hear pronunciation immediately, even before saving.
5. Personal mode supports lookup, pronunciation, and web saving without login or pairing.
6. If the word is not saved yet, edit the meaning if needed and click `Save Word`.
7. If Spring Boot is unavailable, the extension saves locally so the word is not lost.

Fast right-click options:

- `SLSS: Open selected word in popup`: loads the selected word into the popup for review/editing.
- `SLSS: Save selected word`: looks up and saves the selected word immediately.

The toolbar badge shows `WEB` after web quick save, `LOCAL` after fallback local quick save, and `!` if saving fails.

## Package Locally

Run this from the repository root:

```bash
bash firefox-extension/vocab-lookup/package-firefox-extension.sh
```

The packaged add-on is written to:

```text
dist/firefox/slss-vocabulary-lookup-0.1.0.xpi
```

This `.xpi` is suitable for local development/testing. For normal Firefox release installs, Mozilla signing is still required.

## Current Behavior

- Lookup returns Vietnamese translation, English definition, part of speech, phonetic text, pronunciation audio, example sentence, and saved-state metadata.
- Login and pairing are not used by this extension.
- Saves go to `POST /api/v1/vocab/personal/capture` when Spring Boot is running.
- If Spring Boot is unavailable, saved words are stored in Firefox local extension storage.
- If Spring/FastAPI lookup is unavailable or returns no meaning, the extension falls back directly to Free Dictionary API and MyMemory from the popup/background script.
- If a dictionary audio file is unavailable, the popup `Listen` button falls back to Firefox Web Speech pronunciation.
- The right-click quick save calls lookup first, then saves the selected word to the personal web library.
- Duplicate local saves update the existing local word entry.

## Lookup Providers

- Free Dictionary API: English definition, part of speech, phonetic, audio, and examples.
- MyMemory Translation API: English-to-Vietnamese translation.
