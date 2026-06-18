from __future__ import annotations

from pydantic import BaseModel, Field


class VocabularyLookupRequest(BaseModel):
    term: str = Field(min_length=1, max_length=255)
    context_sentence: str | None = Field(default=None, max_length=1000)


class VocabularyLookupResponse(BaseModel):
    term: str
    normalized_term: str
    meaning: str | None = None
    translation_vi: str | None = None
    definition_en: str | None = None
    example_sentence: str | None = None
    part_of_speech: str | None = None
    phonetic: str | None = None
    audio_url: str | None = None
    dictionary_provider: str | None = None
    translation_provider: str | None = None
