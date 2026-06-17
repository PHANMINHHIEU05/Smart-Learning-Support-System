CREATE TABLE IF NOT EXISTS user_settings (
    user_id UUID PRIMARY KEY,
    timezone VARCHAR(100),
    daily_goal_minutes INTEGER,
    pomodoro_focus_minutes INTEGER,
    pomodoro_break_minutes INTEGER,
    pomodoro_long_break_minutes INTEGER,
    pomodoro_cycles_before_long_break INTEGER,
    ai_monitoring_enabled BOOLEAN,
    retention_days INTEGER,
    monitoring_mode VARCHAR(40),
    critical_sound_enabled BOOLEAN,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT chk_user_settings_daily_goal
        CHECK (daily_goal_minutes IS NULL OR (daily_goal_minutes >= 1 AND daily_goal_minutes <= 1440)),
    CONSTRAINT chk_user_settings_focus_minutes
        CHECK (pomodoro_focus_minutes IS NULL OR (pomodoro_focus_minutes >= 1 AND pomodoro_focus_minutes <= 120)),
    CONSTRAINT chk_user_settings_break_minutes
        CHECK (pomodoro_break_minutes IS NULL OR (pomodoro_break_minutes >= 1 AND pomodoro_break_minutes <= 60)),
    CONSTRAINT chk_user_settings_long_break_minutes
        CHECK (pomodoro_long_break_minutes IS NULL OR (pomodoro_long_break_minutes >= 1 AND pomodoro_long_break_minutes <= 120)),
    CONSTRAINT chk_user_settings_cycles
        CHECK (
            pomodoro_cycles_before_long_break IS NULL
            OR (pomodoro_cycles_before_long_break >= 1 AND pomodoro_cycles_before_long_break <= 10)
        ),
    CONSTRAINT chk_user_settings_retention
        CHECK (retention_days IS NULL OR (retention_days >= 1 AND retention_days <= 365)),
    CONSTRAINT chk_user_settings_monitoring_mode
        CHECK (
            monitoring_mode IS NULL
            OR monitoring_mode IN ('browser_camera', 'alerts_only', 'external_camera', 'in_web_widget')
        )
);

ALTER TABLE user_settings
    ADD COLUMN IF NOT EXISTS timezone VARCHAR(100);

ALTER TABLE user_settings
    ADD COLUMN IF NOT EXISTS daily_goal_minutes INTEGER;

ALTER TABLE user_settings
    ADD COLUMN IF NOT EXISTS pomodoro_focus_minutes INTEGER;

ALTER TABLE user_settings
    ADD COLUMN IF NOT EXISTS pomodoro_break_minutes INTEGER;

ALTER TABLE user_settings
    ADD COLUMN IF NOT EXISTS pomodoro_long_break_minutes INTEGER;

ALTER TABLE user_settings
    ADD COLUMN IF NOT EXISTS pomodoro_cycles_before_long_break INTEGER;

ALTER TABLE user_settings
    ADD COLUMN IF NOT EXISTS ai_monitoring_enabled BOOLEAN;

ALTER TABLE user_settings
    ADD COLUMN IF NOT EXISTS retention_days INTEGER;

ALTER TABLE user_settings
    ADD COLUMN IF NOT EXISTS monitoring_mode VARCHAR(40);

ALTER TABLE user_settings
    ADD COLUMN IF NOT EXISTS critical_sound_enabled BOOLEAN;

ALTER TABLE user_settings
    ADD COLUMN IF NOT EXISTS updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW();
