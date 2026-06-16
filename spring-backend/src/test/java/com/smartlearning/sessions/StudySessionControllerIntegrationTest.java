package com.smartlearning.sessions;

import com.smartlearning.tasks.JsonTestSupport;
import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.autoconfigure.web.servlet.AutoConfigureMockMvc;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.http.MediaType;
import org.springframework.security.oauth2.jwt.Jwt;
import org.springframework.test.context.ActiveProfiles;
import org.springframework.test.web.servlet.MockMvc;
import org.springframework.test.web.servlet.request.RequestPostProcessor;

import static org.springframework.security.test.web.servlet.request.SecurityMockMvcRequestPostProcessors.jwt;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.get;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.patch;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.post;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.jsonPath;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

@SpringBootTest(properties = "debug=false")
@AutoConfigureMockMvc
@ActiveProfiles("test")
class StudySessionControllerIntegrationTest {

    private static final String USER_ID = "46068862-dcdc-489b-9aad-94bf05b583e3";

    @Autowired
    private MockMvc mockMvc;

    @Test
    void createAndEndStudySessionForOwnedTask() throws Exception {
        String taskResponse = mockMvc.perform(post("/api/v1/tasks/")
                        .with(userJwt())
                        .contentType(MediaType.APPLICATION_JSON)
                        .content("""
                                {
                                  "title": "Finish grammar set",
                                  "status": "doing"
                                }
                                """))
                .andExpect(status().isCreated())
                .andReturn()
                .getResponse()
                .getContentAsString();

        String taskId = JsonTestSupport.extractString(taskResponse, "task_id");

        String sessionResponse = mockMvc.perform(post("/api/v1/sessions/")
                        .with(userJwt())
                        .contentType(MediaType.APPLICATION_JSON)
                        .content("""
                                {
                                  "task_id": "%s",
                                  "planned_mode": "pomodoro",
                                  "started_at": "2026-06-17T01:00:00Z",
                                  "notes": "first block"
                                }
                                """.formatted(taskId)))
                .andExpect(status().isCreated())
                .andExpect(jsonPath("$.session_id").isNotEmpty())
                .andExpect(jsonPath("$.task_id").value(taskId))
                .andExpect(jsonPath("$.planned_mode").value("pomodoro"))
                .andReturn()
                .getResponse()
                .getContentAsString();

        String sessionId = JsonTestSupport.extractString(sessionResponse, "session_id");

        mockMvc.perform(get("/api/v1/sessions/{sessionId}", sessionId)
                        .with(userJwt()))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.session_id").value(sessionId))
                .andExpect(jsonPath("$.ended_at").doesNotExist());

        mockMvc.perform(patch("/api/v1/sessions/{sessionId}/end", sessionId)
                        .with(userJwt())
                        .contentType(MediaType.APPLICATION_JSON)
                        .content("""
                                {
                                  "ended_at": "2026-06-17T01:25:00Z",
                                  "end_reason": "completed"
                                }
                                """))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.session_id").value(sessionId))
                .andExpect(jsonPath("$.end_reason").value("completed"));

        mockMvc.perform(get("/api/v1/tasks/{taskId}", taskId)
                        .with(userJwt()))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.status").value("done"));
    }

    private static RequestPostProcessor userJwt() {
        return jwt().jwt(Jwt.withTokenValue("test-token")
                .header("alg", "none")
                .subject(USER_ID)
                .build());
    }
}
