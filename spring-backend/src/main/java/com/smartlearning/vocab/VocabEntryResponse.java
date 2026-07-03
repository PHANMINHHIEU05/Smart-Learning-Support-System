package com.smartlearning.vocab;

import com.fasterxml.jackson.annotation.JsonProperty;

import java.math.BigDecimal;
import java.time.OffsetDateTime;
import java.util.UUID;

public record VocabEntryResponse(
        @JsonProperty("vocab_id")
        UUID vocabId,

        @JsonProperty("user_id")
        UUID userId,

        String term,

        String meaning,

        @JsonProperty("translation_vi")
        String translationVi,

        @JsonProperty("definition_en")
        String definitionEn,

        @JsonProperty("example_sentence")
        String exampleSentence,

        String collocation,

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

        VocabStatus status,

        @JsonProperty("ease_factor")
        BigDecimal easeFactor,

        @JsonProperty("interval_days")
        Integer intervalDays,

        @JsonProperty("repetition_count")
        Integer repetitionCount,

        @JsonProperty("study_box")
        Integer studyBox,

        @JsonProperty("next_review_at")
        OffsetDateTime nextReviewAt,

        @JsonProperty("last_reviewed_at")
        OffsetDateTime lastReviewedAt,

        @JsonProperty("created_at")
        OffsetDateTime createdAt,

        @JsonProperty("updated_at")
        OffsetDateTime updatedAt
) {
    public static VocabEntryResponse from(VocabEntry entry) {
        return new VocabEntryResponse(
                entry.getVocabId(),
                entry.getUserId(),
                entry.getTerm(),
                entry.getMeaning(),
                entry.getTranslationVi(),
                entry.getDefinitionEn(),
                entry.getExampleSentence(),
                entry.getCollocation(),
                entry.getPartOfSpeech(),
                entry.getPhonetic(),
                entry.getAudioUrl(),
                entry.getDictionaryProvider(),
                entry.getTranslationProvider(),
                entry.getSourceType(),
                entry.getSourceRef(),
                entry.getStatus(),
                entry.getEaseFactor(),
                entry.getIntervalDays(),
                entry.getRepetitionCount(),
                entry.getStudyBox(),
                entry.getNextReviewAt(),
                entry.getLastReviewedAt(),
                entry.getCreatedAt(),
                entry.getUpdatedAt()
        );
    }
}
