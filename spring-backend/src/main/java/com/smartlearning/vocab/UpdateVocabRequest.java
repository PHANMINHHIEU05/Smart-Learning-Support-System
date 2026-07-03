package com.smartlearning.vocab;

import com.fasterxml.jackson.annotation.JsonProperty;
import jakarta.validation.constraints.Size;
import org.hibernate.validator.constraints.Length;

import java.time.OffsetDateTime;

public record UpdateVocabRequest(
        @Length(max = 255)
        String term,

        String meaning,

        @JsonProperty("example_sentence")
        String exampleSentence,

        String collocation,

        @JsonProperty("part_of_speech")
        @Size(max = 80)
        String partOfSpeech,

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
