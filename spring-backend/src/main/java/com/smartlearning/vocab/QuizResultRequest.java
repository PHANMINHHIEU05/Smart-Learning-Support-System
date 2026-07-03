package com.smartlearning.vocab;

import com.fasterxml.jackson.annotation.JsonProperty;
import jakarta.validation.constraints.NotNull;

import java.time.OffsetDateTime;

public record QuizResultRequest(
        @NotNull
        Boolean correct,

        @JsonProperty("reviewed_at")
        OffsetDateTime reviewedAt
) {
}
