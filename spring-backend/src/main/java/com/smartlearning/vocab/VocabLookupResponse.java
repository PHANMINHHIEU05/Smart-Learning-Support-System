package com.smartlearning.vocab;

import com.fasterxml.jackson.annotation.JsonProperty;

import java.util.UUID;

public record VocabLookupResponse(
        String term,

        @JsonProperty("normalized_term")
        String normalizedTerm,

        String meaning,

        @JsonProperty("translation_vi")
        String translationVi,

        @JsonProperty("definition_en")
        String definitionEn,

        @JsonProperty("example_sentence")
        String exampleSentence,

        @JsonProperty("part_of_speech")
        String partOfSpeech,

        String phonetic,

        @JsonProperty("audio_url")
        String audioUrl,

        @JsonProperty("dictionary_provider")
        String dictionaryProvider,

        @JsonProperty("translation_provider")
        String translationProvider,

        @JsonProperty("source_type")
        String sourceType,

        @JsonProperty("source_ref")
        String sourceRef,

        @JsonProperty("already_saved")
        boolean alreadySaved,

        @JsonProperty("saved_vocab_id")
        UUID savedVocabId,

        @JsonProperty("saved_status")
        VocabStatus savedStatus
) {
}
