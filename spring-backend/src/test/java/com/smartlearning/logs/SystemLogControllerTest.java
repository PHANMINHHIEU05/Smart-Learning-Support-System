package com.smartlearning.logs;

import com.smartlearning.security.SecurityConfig;
import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.autoconfigure.web.servlet.WebMvcTest;
import org.springframework.boot.test.mock.mockito.MockBean;
import org.springframework.context.annotation.Import;
import org.springframework.http.MediaType;
import org.springframework.test.context.TestPropertySource;
import org.springframework.test.web.servlet.MockMvc;

import java.time.OffsetDateTime;
import java.util.UUID;

import static org.mockito.ArgumentMatchers.any;
import static org.mockito.Mockito.when;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.post;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.jsonPath;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

@WebMvcTest(SystemLogController.class)
@Import(SecurityConfig.class)
@TestPropertySource(properties = {
        "app.internal.service-token=test-internal-token",
        "app.security.jwt.enabled=false",
        "debug=false"
})
class SystemLogControllerTest {

    @Autowired
    private MockMvc mockMvc;

    @MockBean
    private SystemLogService service;

    @Test
    void createRejectsRequestWithoutInternalToken() throws Exception {
        mockMvc.perform(post("/api/v1/logs")
                        .contentType(MediaType.APPLICATION_JSON)
                        .content(validBody()))
                .andExpect(status().isUnauthorized());
    }

    @Test
    void createAcceptsRequestWithInternalToken() throws Exception {
        when(service.create(any(CreateSystemLogRequest.class))).thenReturn(new SystemLogResponse(
                UUID.fromString("2ced0f58-b5e0-4a0c-8e42-7aa0b2074d43"),
                "fastapi-ai-worker",
                SystemLogSeverity.ERROR,
                SystemLogCategory.CAMERA,
                "Camera disconnected",
                "manual-test-001",
                OffsetDateTime.parse("2026-06-16T17:50:00Z")
        ));

        mockMvc.perform(post("/api/v1/logs")
                        .header("X-Internal-Service-Token", "test-internal-token")
                        .contentType(MediaType.APPLICATION_JSON)
                        .content(validBody()))
                .andExpect(status().isCreated())
                .andExpect(jsonPath("$.success").value(true))
                .andExpect(jsonPath("$.data.sourceService").value("fastapi-ai-worker"))
                .andExpect(jsonPath("$.data.severity").value("ERROR"))
                .andExpect(jsonPath("$.data.category").value("CAMERA"));
    }

    private static String validBody() {
        return """
                {
                  "sourceService": "fastapi-ai-worker",
                  "severity": "ERROR",
                  "category": "CAMERA",
                  "message": "Camera disconnected",
                  "correlationId": "manual-test-001",
                  "payload": {
                    "cameraIndex": 0,
                    "reason": "device_not_found"
                  }
                }
                """;
    }
}
