package com.smartlearning.sessions;

import com.fasterxml.jackson.annotation.JsonProperty;

import java.time.OffsetDateTime;
import java.util.UUID;

public record StudySessionResponse(
        @JsonProperty("session_id")
        UUID sessionId,

        @JsonProperty("user_id")
        UUID userId,

        @JsonProperty("task_id")
        UUID taskId,

        @JsonProperty("planned_mode")
        SessionMode plannedMode,

        @JsonProperty("started_at")
        OffsetDateTime startedAt,

        @JsonProperty("ended_at")
        OffsetDateTime endedAt,

        @JsonProperty("end_reason")
        SessionEndReason endReason,

        String notes,

        @JsonProperty("created_at")
        OffsetDateTime createdAt
) {
    public static StudySessionResponse from(StudySession session) {
        return new StudySessionResponse(
                session.getSessionId(),
                session.getUserId(),
                session.getTaskId(),
                session.getPlannedMode(),
                session.getStartedAt(),
                session.getEndedAt(),
                session.getEndReason(),
                session.getNotes(),
                session.getCreatedAt()
        );
    }
}
