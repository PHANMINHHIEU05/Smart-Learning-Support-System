package com.smartlearning.logs;

import java.time.OffsetDateTime;
import java.util.UUID;

public record SystemLogResponse(
        UUID logId,
        String sourceService,
        SystemLogSeverity severity,
        SystemLogCategory category,
        String message,
        String correlationId,
        OffsetDateTime createdAt
) {
    public static SystemLogResponse from(SystemLog log) {
        return new SystemLogResponse(
                log.getLogId(),
                log.getSourceService(),
                log.getSeverity(),
                log.getCategory(),
                log.getMessage(),
                log.getCorrelationId(),
                log.getCreatedAt()
        );
    }
}
