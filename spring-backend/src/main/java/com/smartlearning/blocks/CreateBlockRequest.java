package com.smartlearning.blocks;

import com.fasterxml.jackson.annotation.JsonProperty;
import jakarta.validation.constraints.Min;
import jakarta.validation.constraints.NotNull;

import java.time.OffsetDateTime;
import java.util.UUID;

public record CreateBlockRequest(
        @JsonProperty("session_id")
        @NotNull
        UUID sessionId,

        @JsonProperty("block_type")
        @NotNull
        BlockType blockType,

        @JsonProperty("start_at")
        @NotNull
        OffsetDateTime startAt,

        @JsonProperty("end_at")
        OffsetDateTime endAt,

        @JsonProperty("planned_duration_seconds")
        @NotNull
        @Min(1)
        Integer plannedDurationSeconds
) {
}
