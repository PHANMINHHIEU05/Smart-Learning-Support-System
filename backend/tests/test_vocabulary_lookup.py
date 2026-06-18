from __future__ import annotations

import json
import os

import httpx
import pytest
from fastapi import HTTPException

os.environ["DEBUG"] = "false"

from app.core.config import settings
from app.routers.internal_vocabulary import require_internal_token
from app.schemas.vocabulary import VocabularyLookupRequest
from app.services.vocabulary_lookup_service import lookup_vocabulary


@pytest.mark.asyncio
async def test_lookup_combines_dictionary_and_vietnamese_translation(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(settings, "DICTIONARY_API_BASE_URL", "https://dictionary.test")
    monkeypatch.setattr(settings, "TRANSLATION_API_BASE_URL", "https://translation.test")

    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.host == "dictionary.test":
            return httpx.Response(
                200,
                json=[
                    {
                        "word": "consequence",
                        "phonetic": "/ˈkɒn.sɪ.kwens/",
                        "phonetics": [
                            {
                                "text": "/ˈkɒn.sɪ.kwens/",
                                "audio": "//audio.test/consequence.mp3",
                            }
                        ],
                        "meanings": [
                            {
                                "partOfSpeech": "noun",
                                "definitions": [
                                    {
                                        "definition": "a result of a particular action",
                                        "example": "Every action has a consequence.",
                                    }
                                ],
                            }
                        ],
                    }
                ],
            )
        if request.url.host == "translation.test":
            return httpx.Response(
                200,
                json={"responseData": {"translatedText": "hậu quả"}},
            )
        return httpx.Response(404)

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        result = await lookup_vocabulary(
            VocabularyLookupRequest(
                term="Consequence",
                context_sentence="Fallback context sentence.",
            ),
            client=client,
        )

    assert result.normalized_term == "consequence"
    assert result.meaning == "hậu quả"
    assert result.translation_vi == "hậu quả"
    assert result.definition_en == "a result of a particular action"
    assert result.part_of_speech == "noun"
    assert result.phonetic == "/ˈkɒn.sɪ.kwens/"
    assert result.audio_url == "https://audio.test/consequence.mp3"
    assert result.example_sentence == "Every action has a consequence."
    assert result.dictionary_provider == "dictionaryapi.dev"
    assert result.translation_provider == "mymemory"


@pytest.mark.asyncio
async def test_lookup_uses_context_when_providers_are_unavailable(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(settings, "DICTIONARY_API_BASE_URL", "https://dictionary.test")
    monkeypatch.setattr(settings, "TRANSLATION_API_BASE_URL", "https://translation.test")

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(503, text=json.dumps({"detail": "unavailable"}))

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        result = await lookup_vocabulary(
            VocabularyLookupRequest(
                term="Resilient",
                context_sentence="She remained resilient under pressure.",
            ),
            client=client,
        )

    assert result.normalized_term == "resilient"
    assert result.meaning is None
    assert result.example_sentence == "She remained resilient under pressure."
    assert result.dictionary_provider is None
    assert result.translation_provider is None


def test_internal_token_guard_accepts_configured_token(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(settings, "AI_WORKER_INTERNAL_TOKEN", "shared-secret")

    assert require_internal_token("shared-secret") is None


def test_internal_token_guard_rejects_invalid_token(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(settings, "AI_WORKER_INTERNAL_TOKEN", "shared-secret")

    with pytest.raises(HTTPException) as exc:
        require_internal_token("wrong-secret")

    assert exc.value.status_code == 401
