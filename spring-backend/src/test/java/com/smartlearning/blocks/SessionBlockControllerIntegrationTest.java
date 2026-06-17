package com.smartlearning.blocks;

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
class SessionBlockControllerIntegrationTest {

    private static final String USER_ID = "46068862-dcdc-489b-9aad-94bf05b583e3";
    private static final String OTHER_USER_ID = "01b48384-cfa0-460b-84d9-5d3ff7cb5285";

    @Autowired
    private MockMvc mockMvc;

    @Test
    void createListHeartbeatAndCloseLatestBlock() throws Exception {
        String sessionId = createSession(USER_ID, "2026-06-17T01:00:00Z");

        String blockResponse = mockMvc.perform(post("/api/v1/blocks/")
                        .with(userJwt(USER_ID))
                        .contentType(MediaType.APPLICATION_JSON)
                        .content("""
                                {
                                  "session_id": "%s",
                                  "block_type": "focus",
                                  "start_at": "2026-06-17T01:00:00Z",
                                  "planned_duration_seconds": 1500
                                }
                                """.formatted(sessionId)))
                .andExpect(status().isCreated())
                .andExpect(jsonPath("$.block_id").isNotEmpty())
                .andExpect(jsonPath("$.session_id").value(sessionId))
                .andExpect(jsonPath("$.block_type").value("focus"))
                .andExpect(jsonPath("$.started_at").value("2026-06-17T01:00:00Z"))
                .andExpect(jsonPath("$.ended_at").doesNotExist())
                .andExpect(jsonPath("$.planned_duration_seconds").value(1500))
                .andReturn()
                .getResponse()
                .getContentAsString();

        String blockId = JsonTestSupport.extractString(blockResponse, "block_id");

        mockMvc.perform(get("/api/v1/blocks/session/{sessionId}", sessionId)
                        .with(userJwt(USER_ID)))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$[0].block_id").value(blockId))
                .andExpect(jsonPath("$[0].planned_duration_seconds").value(1500));

        mockMvc.perform(patch("/api/v1/blocks/{blockId}/heartbeat", blockId)
                        .with(userJwt(USER_ID))
                        .contentType(MediaType.APPLICATION_JSON)
                        .content("""
                                {
                                  "ended_at": "2026-06-17T01:05:00Z"
                                }
                                """))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.block_id").value(blockId))
                .andExpect(jsonPath("$.ended_at").value("2026-06-17T01:05:00Z"));

        mockMvc.perform(post("/api/v1/blocks/session/{sessionId}/close-latest", sessionId)
                        .with(userJwt(USER_ID)))
                .andExpect(status().isNoContent());
    }

    @Test
    void rejectOverlappingBlock() throws Exception {
        String sessionId = createSession(USER_ID, "2026-06-17T02:00:00Z");

        mockMvc.perform(post("/api/v1/blocks/")
                        .with(userJwt(USER_ID))
                        .contentType(MediaType.APPLICATION_JSON)
                        .content("""
                                {
                                  "session_id": "%s",
                                  "block_type": "focus",
                                  "start_at": "2026-06-17T02:00:00Z",
                                  "end_at": "2026-06-17T02:25:00Z",
                                  "planned_duration_seconds": 1500
                                }
                                """.formatted(sessionId)))
                .andExpect(status().isCreated());

        mockMvc.perform(post("/api/v1/blocks/")
                        .with(userJwt(USER_ID))
                        .contentType(MediaType.APPLICATION_JSON)
                        .content("""
                                {
                                  "session_id": "%s",
                                  "block_type": "break",
                                  "start_at": "2026-06-17T02:24:00Z",
                                  "planned_duration_seconds": 300
                                }
                                """.formatted(sessionId)))
                .andExpect(status().isUnprocessableEntity());
    }

    @Test
    void rejectCrossUserSessionAndBlockAccess() throws Exception {
        String sessionId = createSession(USER_ID, "2026-06-17T03:00:00Z");

        String blockResponse = mockMvc.perform(post("/api/v1/blocks/")
                        .with(userJwt(USER_ID))
                        .contentType(MediaType.APPLICATION_JSON)
                        .content("""
                                {
                                  "session_id": "%s",
                                  "block_type": "focus",
                                  "start_at": "2026-06-17T03:00:00Z",
                                  "planned_duration_seconds": 1500
                                }
                                """.formatted(sessionId)))
                .andExpect(status().isCreated())
                .andReturn()
                .getResponse()
                .getContentAsString();

        String blockId = JsonTestSupport.extractString(blockResponse, "block_id");

        mockMvc.perform(get("/api/v1/blocks/session/{sessionId}", sessionId)
                        .with(userJwt(OTHER_USER_ID)))
                .andExpect(status().isNotFound());

        mockMvc.perform(patch("/api/v1/blocks/{blockId}/heartbeat", blockId)
                        .with(userJwt(OTHER_USER_ID))
                        .contentType(MediaType.APPLICATION_JSON)
                        .content("""
                                {
                                  "ended_at": "2026-06-17T03:05:00Z"
                                }
                                """))
                .andExpect(status().isNotFound());
    }

    private String createSession(String userId, String startedAt) throws Exception {
        String sessionResponse = mockMvc.perform(post("/api/v1/sessions/")
                        .with(userJwt(userId))
                        .contentType(MediaType.APPLICATION_JSON)
                        .content("""
                                {
                                  "planned_mode": "pomodoro",
                                  "started_at": "%s"
                                }
                                """.formatted(startedAt)))
                .andExpect(status().isCreated())
                .andReturn()
                .getResponse()
                .getContentAsString();

        return JsonTestSupport.extractString(sessionResponse, "session_id");
    }

    private static RequestPostProcessor userJwt(String userId) {
        return jwt().jwt(Jwt.withTokenValue("test-token")
                .header("alg", "none")
                .subject(userId)
                .build());
    }
}
