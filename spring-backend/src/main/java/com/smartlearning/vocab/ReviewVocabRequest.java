package com.smartlearning.vocab;

import com.fasterxml.jackson.annotation.JsonProperty;
import jakarta.validation.constraints.NotNull;

import java.time.OffsetDateTime;

public record ReviewVocabRequest(
        @NotNull
        ReviewQuality quality,

        @JsonProperty("reviewed_at")
        OffsetDateTime reviewedAt
) {
}
