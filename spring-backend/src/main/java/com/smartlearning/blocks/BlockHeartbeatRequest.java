package com.smartlearning.blocks;

import com.fasterxml.jackson.annotation.JsonProperty;

import java.time.OffsetDateTime;

public record BlockHeartbeatRequest(
        @JsonProperty("ended_at")
        OffsetDateTime endedAt
) {
}
