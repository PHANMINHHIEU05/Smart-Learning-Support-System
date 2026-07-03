from __future__ import annotations

from contextlib import asynccontextmanager
from typing import Any, AsyncIterator
from urllib.parse import quote

import httpx

from app.core.config import settings
from app.schemas.vocabulary import VocabularyLookupRequest, VocabularyLookupResponse


def _clean_text(value: Any) -> str | None:
    if not isinstance(value, str):
        return None
    cleaned = " ".join(value.split()).strip()
    return cleaned or None


def _normalize_audio_url(value: Any) -> str | None:
    audio_url = _clean_text(value)
    if audio_url and audio_url.startswith("//"):
        return f"https:{audio_url}"
    return audio_url


def _merriam_audio_url(audio: Any) -> str | None:
    audio_name = _clean_text(audio)
    if not audio_name:
        return None

    first = audio_name[0].lower()
    if audio_name.startswith("bix"):
        subdirectory = "bix"
    elif audio_name.startswith("gg"):
        subdirectory = "gg"
    elif not first.isalpha():
        subdirectory = "number"
    else:
        subdirectory = first

    return (
        "https://media.merriam-webster.com/audio/prons/en/us/mp3/"
        f"{subdirectory}/{audio_name}.mp3"
    )


def _first_merriam_webster_result(payload: Any) -> dict[str, str | None]:
    if not isinstance(payload, list):
        return {}

    for entry in payload:
        if not isinstance(entry, dict):
            continue

        definitions = [
            definition
            for definition in entry.get("shortdef") or []
            if _clean_text(definition)
        ]
        definition_en = _clean_text(definitions[0]) if definitions else None
        if not definition_en:
            continue

        headword = entry.get("hwi") if isinstance(entry.get("hwi"), dict) else {}
        phonetic = None
        audio_url = None
        for pronunciation in headword.get("prs") or []:
            if not isinstance(pronunciation, dict):
                continue
            phonetic = phonetic or _clean_text(pronunciation.get("ipa")) or _clean_text(pronunciation.get("mw"))
            sound = pronunciation.get("sound")
            if isinstance(sound, dict):
                audio_url = audio_url or _merriam_audio_url(sound.get("audio"))
            if phonetic and audio_url:
                break

        return {
            "definition_en": definition_en,
            "example_sentence": None,
            "part_of_speech": _clean_text(entry.get("fl")),
            "phonetic": phonetic,
            "audio_url": audio_url,
        }

    return {}


def _first_dictionary_result(payload: Any) -> dict[str, str | None]:
    if not isinstance(payload, list) or not payload or not isinstance(payload[0], dict):
        return {}

    entry = payload[0]
    phonetic = _clean_text(entry.get("phonetic"))
    audio_url = None
    for item in entry.get("phonetics") or []:
        if not isinstance(item, dict):
            continue
        phonetic = phonetic or _clean_text(item.get("text"))
        audio_url = audio_url or _normalize_audio_url(item.get("audio"))
        if phonetic and audio_url:
            break

    for meaning in entry.get("meanings") or []:
        if not isinstance(meaning, dict):
            continue
        part_of_speech = _clean_text(meaning.get("partOfSpeech"))
        for definition in meaning.get("definitions") or []:
            if not isinstance(definition, dict):
                continue
            definition_text = _clean_text(definition.get("definition"))
            if definition_text:
                return {
                    "definition_en": definition_text,
                    "example_sentence": _clean_text(definition.get("example")),
                    "part_of_speech": part_of_speech,
                    "phonetic": phonetic,
                    "audio_url": audio_url,
                }

    return {
        "definition_en": None,
        "example_sentence": None,
        "part_of_speech": None,
        "phonetic": phonetic,
        "audio_url": audio_url,
    }


def _translation_result(payload: Any) -> str | None:
    if not isinstance(payload, dict):
        return None
    response_data = payload.get("responseData")
    if not isinstance(response_data, dict):
        return None
    return _clean_text(response_data.get("translatedText"))


@asynccontextmanager
async def _client_scope(client: httpx.AsyncClient | None) -> AsyncIterator[httpx.AsyncClient]:
    if client is not None:
        yield client
        return

    async with httpx.AsyncClient(timeout=settings.VOCABULARY_HTTP_TIMEOUT_SECONDS) as owned_client:
        yield owned_client


async def lookup_vocabulary(
    request: VocabularyLookupRequest,
    client: httpx.AsyncClient | None = None,
) -> VocabularyLookupResponse:
    term = _clean_text(request.term) or ""
    normalized_term = term.lower()
    dictionary_data: dict[str, str | None] = {}
    dictionary_provider = None
    translation_vi = None

    async with _client_scope(client) as http_client:
        merriam_webster_key = _clean_text(settings.MERRIAM_WEBSTER_LEARNERS_API_KEY)
        if merriam_webster_key:
            try:
                merriam_response = await http_client.get(
                    f"{settings.MERRIAM_WEBSTER_LEARNERS_API_BASE_URL.rstrip('/')}/{quote(normalized_term, safe='')}",
                    params={"key": merriam_webster_key},
                )
                if merriam_response.status_code == 200:
                    dictionary_data = _first_merriam_webster_result(merriam_response.json())
                    if dictionary_data:
                        dictionary_provider = "merriam-webster-learners"
            except (httpx.HTTPError, ValueError):
                dictionary_data = {}

        try:
            if not dictionary_data:
                dictionary_response = await http_client.get(
                    f"{settings.DICTIONARY_API_BASE_URL.rstrip('/')}/api/v2/entries/en/{quote(normalized_term, safe='')}"
                )
                if dictionary_response.status_code == 200:
                    dictionary_data = _first_dictionary_result(dictionary_response.json())
                    if dictionary_data:
                        dictionary_provider = "dictionaryapi.dev"
        except (httpx.HTTPError, ValueError):
            dictionary_data = {}

        try:
            translation_response = await http_client.get(
                f"{settings.TRANSLATION_API_BASE_URL.rstrip('/')}/get",
                params={"q": term, "langpair": "en|vi"},
            )
            if translation_response.status_code == 200:
                translation_vi = _translation_result(translation_response.json())
        except (httpx.HTTPError, ValueError):
            translation_vi = None

    example_sentence = dictionary_data.get("example_sentence") or _clean_text(request.context_sentence)
    definition_en = dictionary_data.get("definition_en")

    return VocabularyLookupResponse(
        term=term,
        normalized_term=normalized_term,
        meaning=translation_vi or definition_en,
        translation_vi=translation_vi,
        definition_en=definition_en,
        example_sentence=example_sentence,
        part_of_speech=dictionary_data.get("part_of_speech"),
        phonetic=dictionary_data.get("phonetic"),
        audio_url=dictionary_data.get("audio_url"),
        dictionary_provider=dictionary_provider,
        translation_provider="mymemory" if translation_vi else None,
    )
