package com.smartlearning.tasks;

import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.autoconfigure.web.servlet.AutoConfigureMockMvc;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.http.MediaType;
import org.springframework.security.oauth2.jwt.Jwt;
import org.springframework.test.context.ActiveProfiles;
import org.springframework.test.web.servlet.MockMvc;
import org.springframework.test.web.servlet.request.RequestPostProcessor;

import static org.hamcrest.Matchers.hasSize;
import static org.springframework.security.test.web.servlet.request.SecurityMockMvcRequestPostProcessors.jwt;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.get;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.patch;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.post;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.jsonPath;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

@SpringBootTest(properties = "debug=false")
@AutoConfigureMockMvc
@ActiveProfiles("test")
class TaskControllerIntegrationTest {

    private static final String USER_ID = "35b6a11d-09c8-4b90-93f4-5ecb69db17d9";

    @Autowired
    private MockMvc mockMvc;

    @Test
    void taskCrudUsesAuthenticatedUserBoundary() throws Exception {
        String createResponse = mockMvc.perform(post("/api/v1/tasks/")
                        .with(userJwt())
                        .contentType(MediaType.APPLICATION_JSON)
                        .content("""
                                {
                                  "title": "Read English article",
                                  "description": "Prepare vocabulary notes",
                                  "status": "todo",
                                  "priority": 5,
                                  "estimated_minutes": 30,
                                  "subject_name": "English",
                                  "tags_json": {
                                    "source": "manual"
                                  }
                                }
                                """))
                .andExpect(status().isCreated())
                .andExpect(jsonPath("$.task_id").isNotEmpty())
                .andExpect(jsonPath("$.user_id").value(USER_ID))
                .andExpect(jsonPath("$.title").value("Read English article"))
                .andExpect(jsonPath("$.status").value("todo"))
                .andExpect(jsonPath("$.estimated_minutes").value(30))
                .andReturn()
                .getResponse()
                .getContentAsString();

        String taskId = JsonTestSupport.extractString(createResponse, "task_id");

        mockMvc.perform(get("/api/v1/tasks/?status=todo&limit=50")
                        .with(userJwt()))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$", hasSize(1)))
                .andExpect(jsonPath("$[0].task_id").value(taskId));

        mockMvc.perform(patch("/api/v1/tasks/{taskId}", taskId)
                        .with(userJwt())
                        .contentType(MediaType.APPLICATION_JSON)
                        .content("""
                                {
                                  "status": "doing",
                                  "priority": 7
                                }
                                """))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.task_id").value(taskId))
                .andExpect(jsonPath("$.status").value("doing"))
                .andExpect(jsonPath("$.priority").value(7));

        mockMvc.perform(get("/api/v1/tasks/{taskId}", taskId)
                        .with(userJwt()))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.task_id").value(taskId))
                .andExpect(jsonPath("$.status").value("doing"));
    }

    private static RequestPostProcessor userJwt() {
        return jwt().jwt(Jwt.withTokenValue("test-token")
                .header("alg", "none")
                .subject(USER_ID)
                .build());
    }
}
