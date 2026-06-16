package com.smartlearning.tasks;

import com.fasterxml.jackson.annotation.JsonProperty;

import java.time.OffsetDateTime;
import java.util.Map;
import java.util.UUID;

public record TaskResponse(
        @JsonProperty("task_id")
        UUID taskId,

        @JsonProperty("user_id")
        UUID userId,

        String title,

        String description,

        TaskStatus status,

        Integer priority,

        @JsonProperty("due_at")
        OffsetDateTime dueAt,

        @JsonProperty("estimated_minutes")
        Integer estimatedMinutes,

        @JsonProperty("subject_name")
        String subjectName,

        @JsonProperty("tags_json")
        Map<String, Object> tagsJson,

        @JsonProperty("created_at")
        OffsetDateTime createdAt,

        @JsonProperty("updated_at")
        OffsetDateTime updatedAt
) {
    public static TaskResponse from(Task task) {
        return new TaskResponse(
                task.getTaskId(),
                task.getUserId(),
                task.getTitle(),
                task.getDescription(),
                task.getStatus(),
                task.getPriority(),
                task.getDueAt(),
                task.getEstimatedMinutes(),
                task.getSubjectName(),
                task.getTagsJson(),
                task.getCreatedAt(),
                task.getUpdatedAt()
        );
    }
}
