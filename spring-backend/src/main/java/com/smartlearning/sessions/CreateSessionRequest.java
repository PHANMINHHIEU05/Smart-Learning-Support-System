package com.smartlearning.sessions;

import com.fasterxml.jackson.annotation.JsonProperty;
import jakarta.validation.constraints.NotNull;

import java.time.OffsetDateTime;
import java.util.UUID;

public record CreateSessionRequest(
        @JsonProperty("task_id")
        UUID taskId,

        @JsonProperty("planned_mode")
        SessionMode plannedMode,

        @JsonProperty("started_at")
        @NotNull
        OffsetDateTime startedAt,

        String notes
) {
}
