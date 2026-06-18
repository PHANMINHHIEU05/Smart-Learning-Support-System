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

        @JsonProperty("example_sentence")
        String exampleSentence,

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
                entry.getExampleSentence(),
                entry.getSourceType(),
                entry.getSourceRef(),
                entry.getStatus(),
                entry.getEaseFactor(),
                entry.getIntervalDays(),
                entry.getRepetitionCount(),
                entry.getNextReviewAt(),
                entry.getLastReviewedAt(),
                entry.getCreatedAt(),
                entry.getUpdatedAt()
        );
    }
}
