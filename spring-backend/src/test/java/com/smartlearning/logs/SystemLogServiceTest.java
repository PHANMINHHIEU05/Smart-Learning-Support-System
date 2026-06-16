package com.smartlearning.logs;

import org.junit.jupiter.api.Test;

import java.time.OffsetDateTime;
import java.util.Map;

import static org.assertj.core.api.Assertions.assertThat;
import static org.mockito.ArgumentMatchers.any;
import static org.mockito.Mockito.mock;
import static org.mockito.Mockito.verify;
import static org.mockito.Mockito.when;

class SystemLogServiceTest {

    private final SystemLogRepository repository = mock(SystemLogRepository.class);
    private final SystemLogService service = new SystemLogService(repository);

    @Test
    void createPersistsSystemLogFromRequest() {
        when(repository.save(any(SystemLog.class))).thenAnswer(invocation -> {
            SystemLog log = invocation.getArgument(0);
            log.setCreatedAt(OffsetDateTime.now());
            return log;
        });

        CreateSystemLogRequest request = new CreateSystemLogRequest(
                "fastapi-ai-worker",
                SystemLogSeverity.ERROR,
                SystemLogCategory.CAMERA,
                "Camera disconnected",
                "manual-test-001",
                Map.of("cameraIndex", 0, "reason", "device_not_found")
        );

        SystemLogResponse response = service.create(request);

        assertThat(response.sourceService()).isEqualTo("fastapi-ai-worker");
        assertThat(response.severity()).isEqualTo(SystemLogSeverity.ERROR);
        assertThat(response.category()).isEqualTo(SystemLogCategory.CAMERA);
        assertThat(response.message()).isEqualTo("Camera disconnected");
        assertThat(response.correlationId()).isEqualTo("manual-test-001");
        assertThat(response.createdAt()).isNotNull();
        verify(repository).save(any(SystemLog.class));
    }
}
