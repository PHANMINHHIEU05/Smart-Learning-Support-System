package com.smartlearning.sessions;

import com.fasterxml.jackson.annotation.JsonProperty;
import jakarta.validation.constraints.NotNull;

import java.time.OffsetDateTime;

public record EndSessionRequest(
        @JsonProperty("ended_at")
        @NotNull
        OffsetDateTime endedAt,

        @JsonProperty("end_reason")
        SessionEndReason endReason,

        String notes
) {
}
