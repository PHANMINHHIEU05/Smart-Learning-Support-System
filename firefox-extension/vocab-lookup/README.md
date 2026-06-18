# SLSS Vocabulary Lookup Firefox Extension

## Purpose

This extension captures a selected English word from Firefox and saves it into the Smart Learning Support System vocabulary library through Spring Boot.

## Local Setup

1. Start Spring Boot at `http://localhost:8080`.
2. Start the frontend and log in.
3. Open the web app Vocabulary page.
4. Click `Copy Extension Token`.
5. In Firefox, open `about:debugging#/runtime/this-firefox`.
6. Click `Load Temporary Add-on`.
7. Select `manifest.json` from this folder.
8. Open the extension popup and paste the copied token.

## Use

1. Select a word on any webpage.
2. Open the extension popup or use the context menu `Capture word in SLSS`.
3. Edit the meaning if needed.
4. Click `Save Word`.

## Current Behavior

- Lookup returns Vietnamese translation, English definition, part of speech, phonetic text, pronunciation audio, example sentence, and saved-state metadata.
- Save calls `POST /api/v1/vocab/capture`.
- Duplicate captures return the existing vocabulary entry instead of creating a second row.

## Lookup Providers

- Free Dictionary API: English definition, part of speech, phonetic, audio, and examples.
- MyMemory Translation API: English-to-Vietnamese translation.
- Spring calls FastAPI for enrichment and remains responsible for authentication, persistence, and SRS.
