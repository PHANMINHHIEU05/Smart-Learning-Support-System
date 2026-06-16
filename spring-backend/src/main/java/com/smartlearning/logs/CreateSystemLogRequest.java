package com.smartlearning.logs;

import jakarta.validation.constraints.NotBlank;
import jakarta.validation.constraints.NotNull;
import jakarta.validation.constraints.Size;

import java.util.LinkedHashMap;
import java.util.Map;

public record CreateSystemLogRequest(
        @NotBlank
        @Size(max = 100)
        String sourceService,

        @NotNull
        SystemLogSeverity severity,

        @NotNull
        SystemLogCategory category,

        @NotBlank
        @Size(max = 2000)
        String message,

        @Size(max = 120)
        String correlationId,

        Map<String, Object> payload
) {
    public Map<String, Object> safePayload() {
        return payload == null ? new LinkedHashMap<>() : payload;
    }
}
