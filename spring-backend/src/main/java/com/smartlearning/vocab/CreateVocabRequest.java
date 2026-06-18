package com.smartlearning.vocab;

import com.fasterxml.jackson.annotation.JsonProperty;
import jakarta.validation.constraints.Size;
import org.hibernate.validator.constraints.Length;
import org.hibernate.validator.constraints.NotBlank;

import java.time.OffsetDateTime;

public record CreateVocabRequest(
        @NotBlank
        @Length(max = 255)
        String term,

        String meaning,

        @JsonProperty("example_sentence")
        String exampleSentence,

        @JsonProperty("source_type")
        @Size(max = 40)
        String sourceType,

        @JsonProperty("source_ref")
        String sourceRef,

        VocabStatus status,

        @JsonProperty("next_review_at")
        OffsetDateTime nextReviewAt
) {
}
