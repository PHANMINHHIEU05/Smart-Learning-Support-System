package com.smartlearning.settings;

import com.fasterxml.jackson.annotation.JsonProperty;

import java.time.OffsetDateTime;
import java.util.UUID;

public record UserSettingResponse(
        @JsonProperty("user_id")
        UUID userId,

        String timezone,

        @JsonProperty("daily_goal_minutes")
        Integer dailyGoalMinutes,

        @JsonProperty("pomodoro_focus_minutes")
        Integer pomodoroFocusMinutes,

        @JsonProperty("pomodoro_break_minutes")
        Integer pomodoroBreakMinutes,

        @JsonProperty("pomodoro_long_break_minutes")
        Integer pomodoroLongBreakMinutes,

        @JsonProperty("pomodoro_cycles_before_long_break")
        Integer pomodoroCyclesBeforeLongBreak,

        @JsonProperty("ai_monitoring_enabled")
        Boolean aiMonitoringEnabled,

        @JsonProperty("retention_days")
        Integer retentionDays,

        @JsonProperty("monitoring_mode")
        String monitoringMode,

        @JsonProperty("critical_sound_enabled")
        Boolean criticalSoundEnabled,

        @JsonProperty("updated_at")
        OffsetDateTime updatedAt
) {
    public static UserSettingResponse from(UserSetting setting) {
        return new UserSettingResponse(
                setting.getUserId(),
                setting.getTimezone(),
                setting.getDailyGoalMinutes(),
                setting.getPomodoroFocusMinutes(),
                setting.getPomodoroBreakMinutes(),
                setting.getPomodoroLongBreakMinutes(),
                setting.getPomodoroCyclesBeforeLongBreak(),
                setting.getAiMonitoringEnabled(),
                setting.getRetentionDays(),
                setting.getMonitoringMode(),
                setting.getCriticalSoundEnabled(),
                setting.getUpdatedAt()
        );
    }
}
