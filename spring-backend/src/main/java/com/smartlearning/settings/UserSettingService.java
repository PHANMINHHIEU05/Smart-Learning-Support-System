package com.smartlearning.settings;

import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import java.util.UUID;

@Service
public class UserSettingService {

    private static final String DEFAULT_TIMEZONE = "UTC";
    private static final int DEFAULT_DAILY_GOAL_MINUTES = 120;
    private static final int DEFAULT_FOCUS_MINUTES = 25;
    private static final int DEFAULT_BREAK_MINUTES = 5;
    private static final int DEFAULT_LONG_BREAK_MINUTES = 15;
    private static final int DEFAULT_CYCLES_BEFORE_LONG_BREAK = 4;
    private static final boolean DEFAULT_AI_MONITORING_ENABLED = true;
    private static final int DEFAULT_RETENTION_DAYS = 30;
    private static final String DEFAULT_MONITORING_MODE = "browser_camera";
    private static final boolean DEFAULT_CRITICAL_SOUND_ENABLED = true;

    private final UserSettingRepository repository;

    public UserSettingService(UserSettingRepository repository) {
        this.repository = repository;
    }

    @Transactional
    public UserSettingResponse getOrCreate(UUID userId) {
        return repository.findById(userId)
                .map(this::normalizeLegacyModeForRead)
                .map(UserSettingResponse::from)
                .orElseGet(() -> UserSettingResponse.from(repository.save(createDefault(userId))));
    }

    @Transactional
    public UserSettingResponse update(UUID userId, UserSettingUpdateRequest request) {
        UserSetting setting = repository.findById(userId)
                .orElseGet(() -> createDefault(userId));

        applyUpdates(setting, request);
        return UserSettingResponse.from(repository.save(setting));
    }

    private UserSetting createDefault(UUID userId) {
        UserSetting setting = new UserSetting();
        setting.setUserId(userId);
        setting.setTimezone(DEFAULT_TIMEZONE);
        setting.setDailyGoalMinutes(DEFAULT_DAILY_GOAL_MINUTES);
        setting.setPomodoroFocusMinutes(DEFAULT_FOCUS_MINUTES);
        setting.setPomodoroBreakMinutes(DEFAULT_BREAK_MINUTES);
        setting.setPomodoroLongBreakMinutes(DEFAULT_LONG_BREAK_MINUTES);
        setting.setPomodoroCyclesBeforeLongBreak(DEFAULT_CYCLES_BEFORE_LONG_BREAK);
        setting.setAiMonitoringEnabled(DEFAULT_AI_MONITORING_ENABLED);
        setting.setRetentionDays(DEFAULT_RETENTION_DAYS);
        setting.setMonitoringMode(DEFAULT_MONITORING_MODE);
        setting.setCriticalSoundEnabled(DEFAULT_CRITICAL_SOUND_ENABLED);
        return setting;
    }

    private UserSetting normalizeLegacyModeForRead(UserSetting setting) {
        String normalized = normalizeMonitoringMode(setting.getMonitoringMode());
        if (!normalized.equals(setting.getMonitoringMode())) {
            setting.setMonitoringMode(normalized);
            return repository.save(setting);
        }
        return setting;
    }

    private void applyUpdates(UserSetting setting, UserSettingUpdateRequest request) {
        if (request.timezone() != null) {
            setting.setTimezone(request.timezone());
        }
        if (request.dailyGoalMinutes() != null) {
            setting.setDailyGoalMinutes(request.dailyGoalMinutes());
        }
        if (request.pomodoroFocusMinutes() != null) {
            setting.setPomodoroFocusMinutes(request.pomodoroFocusMinutes());
        }
        if (request.pomodoroBreakMinutes() != null) {
            setting.setPomodoroBreakMinutes(request.pomodoroBreakMinutes());
        }
        if (request.pomodoroLongBreakMinutes() != null) {
            setting.setPomodoroLongBreakMinutes(request.pomodoroLongBreakMinutes());
        }
        if (request.pomodoroCyclesBeforeLongBreak() != null) {
            setting.setPomodoroCyclesBeforeLongBreak(request.pomodoroCyclesBeforeLongBreak());
        }
        if (request.aiMonitoringEnabled() != null) {
            setting.setAiMonitoringEnabled(request.aiMonitoringEnabled());
        }
        if (request.retentionDays() != null) {
            setting.setRetentionDays(request.retentionDays());
        }
        if (request.monitoringMode() != null) {
            setting.setMonitoringMode(normalizeMonitoringMode(request.monitoringMode()));
        }
        if (request.criticalSoundEnabled() != null) {
            setting.setCriticalSoundEnabled(request.criticalSoundEnabled());
        }
    }

    private static String normalizeMonitoringMode(String mode) {
        if (mode == null || mode.isBlank()) {
            return DEFAULT_MONITORING_MODE;
        }
        if ("in_web_widget".equals(mode) || "external_camera".equals(mode)) {
            return DEFAULT_MONITORING_MODE;
        }
        if ("browser_camera".equals(mode) || "alerts_only".equals(mode)) {
            return mode;
        }
        return DEFAULT_MONITORING_MODE;
    }
}
