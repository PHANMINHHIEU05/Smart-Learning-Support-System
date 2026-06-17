package com.smartlearning.settings;

import jakarta.persistence.Column;
import jakarta.persistence.Entity;
import jakarta.persistence.Id;
import jakarta.persistence.PrePersist;
import jakarta.persistence.PreUpdate;
import jakarta.persistence.Table;

import java.time.OffsetDateTime;
import java.util.UUID;

@Entity
@Table(name = "user_settings")
public class UserSetting {

    @Id
    @Column(name = "user_id", nullable = false)
    private UUID userId;

    @Column(name = "timezone", length = 100)
    private String timezone;

    @Column(name = "daily_goal_minutes")
    private Integer dailyGoalMinutes;

    @Column(name = "pomodoro_focus_minutes")
    private Integer pomodoroFocusMinutes;

    @Column(name = "pomodoro_break_minutes")
    private Integer pomodoroBreakMinutes;

    @Column(name = "pomodoro_long_break_minutes")
    private Integer pomodoroLongBreakMinutes;

    @Column(name = "pomodoro_cycles_before_long_break")
    private Integer pomodoroCyclesBeforeLongBreak;

    @Column(name = "ai_monitoring_enabled")
    private Boolean aiMonitoringEnabled;

    @Column(name = "retention_days")
    private Integer retentionDays;

    @Column(name = "monitoring_mode", length = 40)
    private String monitoringMode;

    @Column(name = "critical_sound_enabled")
    private Boolean criticalSoundEnabled;

    @Column(name = "updated_at", nullable = false)
    private OffsetDateTime updatedAt;

    @PrePersist
    @PreUpdate
    void touchUpdatedAt() {
        updatedAt = OffsetDateTime.now();
    }

    public UUID getUserId() {
        return userId;
    }

    public void setUserId(UUID userId) {
        this.userId = userId;
    }

    public String getTimezone() {
        return timezone;
    }

    public void setTimezone(String timezone) {
        this.timezone = timezone;
    }

    public Integer getDailyGoalMinutes() {
        return dailyGoalMinutes;
    }

    public void setDailyGoalMinutes(Integer dailyGoalMinutes) {
        this.dailyGoalMinutes = dailyGoalMinutes;
    }

    public Integer getPomodoroFocusMinutes() {
        return pomodoroFocusMinutes;
    }

    public void setPomodoroFocusMinutes(Integer pomodoroFocusMinutes) {
        this.pomodoroFocusMinutes = pomodoroFocusMinutes;
    }

    public Integer getPomodoroBreakMinutes() {
        return pomodoroBreakMinutes;
    }

    public void setPomodoroBreakMinutes(Integer pomodoroBreakMinutes) {
        this.pomodoroBreakMinutes = pomodoroBreakMinutes;
    }

    public Integer getPomodoroLongBreakMinutes() {
        return pomodoroLongBreakMinutes;
    }

    public void setPomodoroLongBreakMinutes(Integer pomodoroLongBreakMinutes) {
        this.pomodoroLongBreakMinutes = pomodoroLongBreakMinutes;
    }

    public Integer getPomodoroCyclesBeforeLongBreak() {
        return pomodoroCyclesBeforeLongBreak;
    }

    public void setPomodoroCyclesBeforeLongBreak(Integer pomodoroCyclesBeforeLongBreak) {
        this.pomodoroCyclesBeforeLongBreak = pomodoroCyclesBeforeLongBreak;
    }

    public Boolean getAiMonitoringEnabled() {
        return aiMonitoringEnabled;
    }

    public void setAiMonitoringEnabled(Boolean aiMonitoringEnabled) {
        this.aiMonitoringEnabled = aiMonitoringEnabled;
    }

    public Integer getRetentionDays() {
        return retentionDays;
    }

    public void setRetentionDays(Integer retentionDays) {
        this.retentionDays = retentionDays;
    }

    public String getMonitoringMode() {
        return monitoringMode;
    }

    public void setMonitoringMode(String monitoringMode) {
        this.monitoringMode = monitoringMode;
    }

    public Boolean getCriticalSoundEnabled() {
        return criticalSoundEnabled;
    }

    public void setCriticalSoundEnabled(Boolean criticalSoundEnabled) {
        this.criticalSoundEnabled = criticalSoundEnabled;
    }

    public OffsetDateTime getUpdatedAt() {
        return updatedAt;
    }
}
