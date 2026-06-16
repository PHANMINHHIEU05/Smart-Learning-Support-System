package com.smartlearning.tasks;

import com.fasterxml.jackson.annotation.JsonProperty;
import jakarta.validation.constraints.Max;
import jakarta.validation.constraints.Min;
import jakarta.validation.constraints.Size;

import java.time.OffsetDateTime;
import java.util.Map;

public record UpdateTaskRequest(
        @Size(min = 1, max = 255)
        String title,

        String description,

        TaskStatus status,

        @Min(0)
        @Max(10)
        Integer priority,

        @JsonProperty("due_at")
        OffsetDateTime dueAt,

        @JsonProperty("estimated_minutes")
        @Min(1)
        Integer estimatedMinutes,

        @JsonProperty("subject_name")
        @Size(max = 255)
        String subjectName,

        @JsonProperty("tags_json")
        Map<String, Object> tagsJson
) {
}
