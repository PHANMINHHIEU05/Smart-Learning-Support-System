package com.smartlearning.settings;

import com.fasterxml.jackson.annotation.JsonProperty;
import jakarta.validation.constraints.Max;
import jakarta.validation.constraints.Min;
import jakarta.validation.constraints.Pattern;
import jakarta.validation.constraints.Size;

public record UserSettingUpdateRequest(
        @Size(max = 100)
        String timezone,

        @JsonProperty("daily_goal_minutes")
        @Min(1)
        @Max(1440)
        Integer dailyGoalMinutes,

        @JsonProperty("pomodoro_focus_minutes")
        @Min(1)
        @Max(120)
        Integer pomodoroFocusMinutes,

        @JsonProperty("pomodoro_break_minutes")
        @Min(1)
        @Max(60)
        Integer pomodoroBreakMinutes,

        @JsonProperty("pomodoro_long_break_minutes")
        @Min(1)
        @Max(120)
        Integer pomodoroLongBreakMinutes,

        @JsonProperty("pomodoro_cycles_before_long_break")
        @Min(1)
        @Max(10)
        Integer pomodoroCyclesBeforeLongBreak,

        @JsonProperty("ai_monitoring_enabled")
        Boolean aiMonitoringEnabled,

        @JsonProperty("retention_days")
        @Min(1)
        @Max(365)
        Integer retentionDays,

        @JsonProperty("monitoring_mode")
        @Pattern(regexp = "^(browser_camera|alerts_only|external_camera|in_web_widget)$")
        String monitoringMode,

        @JsonProperty("critical_sound_enabled")
        Boolean criticalSoundEnabled
) {
}
