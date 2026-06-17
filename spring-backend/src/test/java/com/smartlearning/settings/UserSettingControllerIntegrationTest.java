package com.smartlearning.settings;

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
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.put;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.jsonPath;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

@SpringBootTest(properties = "debug=false")
@AutoConfigureMockMvc
@ActiveProfiles("test")
class UserSettingControllerIntegrationTest {

    private static final String USER_ID = "46068862-dcdc-489b-9aad-94bf05b583e3";

    @Autowired
    private MockMvc mockMvc;

    @Test
    void getCreatesDefaultSettingsForCurrentUser() throws Exception {
        mockMvc.perform(get("/api/v1/settings/")
                        .with(userJwt()))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.user_id").value(USER_ID))
                .andExpect(jsonPath("$.timezone").value("UTC"))
                .andExpect(jsonPath("$.daily_goal_minutes").value(120))
                .andExpect(jsonPath("$.pomodoro_focus_minutes").value(25))
                .andExpect(jsonPath("$.pomodoro_break_minutes").value(5))
                .andExpect(jsonPath("$.pomodoro_long_break_minutes").value(15))
                .andExpect(jsonPath("$.pomodoro_cycles_before_long_break").value(4))
                .andExpect(jsonPath("$.ai_monitoring_enabled").value(true))
                .andExpect(jsonPath("$.retention_days").value(30))
                .andExpect(jsonPath("$.monitoring_mode").value("browser_camera"))
                .andExpect(jsonPath("$.critical_sound_enabled").value(true))
                .andExpect(jsonPath("$.updated_at").isNotEmpty());
    }

    @Test
    void updateSettingsNormalizesLegacyMonitoringMode() throws Exception {
        mockMvc.perform(put("/api/v1/settings/")
                        .with(userJwt())
                        .contentType(MediaType.APPLICATION_JSON)
                        .content("""
                                {
                                  "timezone": "Asia/Ho_Chi_Minh",
                                  "daily_goal_minutes": 180,
                                  "pomodoro_focus_minutes": 45,
                                  "pomodoro_break_minutes": 10,
                                  "pomodoro_long_break_minutes": 20,
                                  "pomodoro_cycles_before_long_break": 3,
                                  "ai_monitoring_enabled": false,
                                  "retention_days": 60,
                                  "monitoring_mode": "external_camera",
                                  "critical_sound_enabled": false
                                }
                                """))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.timezone").value("Asia/Ho_Chi_Minh"))
                .andExpect(jsonPath("$.daily_goal_minutes").value(180))
                .andExpect(jsonPath("$.pomodoro_focus_minutes").value(45))
                .andExpect(jsonPath("$.pomodoro_break_minutes").value(10))
                .andExpect(jsonPath("$.pomodoro_long_break_minutes").value(20))
                .andExpect(jsonPath("$.pomodoro_cycles_before_long_break").value(3))
                .andExpect(jsonPath("$.ai_monitoring_enabled").value(false))
                .andExpect(jsonPath("$.retention_days").value(60))
                .andExpect(jsonPath("$.monitoring_mode").value("browser_camera"))
                .andExpect(jsonPath("$.critical_sound_enabled").value(false));
    }

    @Test
    void rejectInvalidSettingsValues() throws Exception {
        mockMvc.perform(put("/api/v1/settings/")
                        .with(userJwt())
                        .contentType(MediaType.APPLICATION_JSON)
                        .content("""
                                {
                                  "pomodoro_focus_minutes": 121
                                }
                                """))
                .andExpect(status().isBadRequest());
    }

    private static RequestPostProcessor userJwt() {
        return jwt().jwt(Jwt.withTokenValue("test-token")
                .header("alg", "none")
                .subject(USER_ID)
                .build());
    }
}
