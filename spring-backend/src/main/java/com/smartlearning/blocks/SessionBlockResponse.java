package com.smartlearning.blocks;

import com.fasterxml.jackson.annotation.JsonProperty;

import java.time.OffsetDateTime;
import java.util.UUID;

public record SessionBlockResponse(
        @JsonProperty("block_id")
        UUID blockId,

        @JsonProperty("session_id")
        UUID sessionId,

        @JsonProperty("block_type")
        BlockType blockType,

        @JsonProperty("started_at")
        OffsetDateTime startedAt,

        @JsonProperty("ended_at")
        OffsetDateTime endedAt,

        @JsonProperty("planned_duration_seconds")
        Integer plannedDurationSeconds
) {
    public static SessionBlockResponse from(SessionBlock block) {
        return new SessionBlockResponse(
                block.getBlockId(),
                block.getSessionId(),
                block.getBlockType(),
                block.getStartAt(),
                block.getEndAt(),
                block.getPlannedDurationSeconds()
        );
    }
}
