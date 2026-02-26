# 2️⃣ ERD — Entity Relationship Diagram

Source DBML: [`database/erd.dbml`](../../database/erd.dbml) — paste vào [dbdiagram.io](https://dbdiagram.io) để xem bản đẹp.

```mermaid
erDiagram
    users {
        uuid    user_id      PK
        varchar email        UK
        varchar password_hash
        varchar display_name
        timestamptz created_at
        timestamptz updated_at
    }

    user_settings {
        uuid    user_id                           PK "FK → users"
        varchar timezone
        int     daily_goal_minutes
        int     pomodoro_focus_minutes
        int     pomodoro_break_minutes
        int     pomodoro_long_break_minutes
        int     pomodoro_cycles_before_long_break
        boolean ai_monitoring_enabled
        int     retention_days
        timestamptz updated_at
    }

    tasks {
        uuid    task_id           PK
        uuid    user_id           FK
        varchar title
        text    description
        varchar status            "todo/doing/done/archived"
        int     priority
        timestamptz due_at
        int     estimated_minutes
        varchar subject_name
        json    tags_json
        timestamptz created_at
        timestamptz updated_at
    }

    study_sessions {
        uuid    session_id   PK
        uuid    user_id      FK
        uuid    task_id      FK "nullable"
        varchar planned_mode "pomodoro | free"
        timestamptz started_at
        timestamptz ended_at
        varchar end_reason   "completed/stopped/timeout/error"
        text    notes
        timestamptz created_at
    }

    session_blocks {
        uuid    block_id    PK
        uuid    session_id  FK
        varchar block_type  "focus/break/long_break"
        timestamptz start_at
        timestamptz end_at
    }

    ai_events {
        uuid    event_id     PK
        uuid    user_id      FK
        uuid    session_id   FK "nullable"
        varchar event_type   "POSTURE_SLOUCH/FOCUS_OFFSCREEN/PHONE/FATIGUE_YAWN/..."
        timestamptz start_at
        timestamptz end_at
        float   confidence
        int     severity
        json    payload_json
    }

    alert_rules {
        uuid    rule_id              PK
        uuid    user_id              FK
        varchar name
        boolean is_enabled
        varchar trigger_event_type
        int     cooldown_seconds
        json    condition_json
        json    action_json
        timestamptz created_at
        timestamptz updated_at
    }

    alerts {
        uuid    alert_id    PK
        uuid    user_id     FK
        uuid    session_id  FK "nullable"
        uuid    rule_id     FK "nullable"
        uuid    event_id    FK "nullable"
        timestamptz fired_at
        varchar channel     "toast/sound"
        varchar message
        json    payload_json
    }

    users          ||--o|  user_settings  : "1:1 settings"
    users          ||--o{  tasks          : "owns"
    users          ||--o{  study_sessions : "studies"
    users          ||--o{  ai_events      : "monitored by"
    users          ||--o{  alert_rules    : "configures"
    users          ||--o{  alerts         : "receives"

    tasks          ||--o{  study_sessions : "worked on in"
    study_sessions ||--o{  session_blocks : "split into blocks"
    study_sessions ||--o{  ai_events      : "events during"
    study_sessions ||--o{  alerts         : "alerts fired in"

    alert_rules    ||--o{  alerts         : "triggers"
    ai_events      ||--o{  alerts         : "causes"
```

## Ghi chú indexes

| Bảng | Index |
|------|-------|
| `tasks` | `(user_id, status)`, `(user_id, due_at)` |
| `study_sessions` | `(user_id, started_at)`, `(task_id, started_at)` |
| `session_blocks` | `(session_id, start_at)` |
| `ai_events` | `(user_id, start_at)`, `(session_id, start_at)`, `(event_type, start_at)` |
| `alert_rules` | `(user_id, is_enabled)`, `(trigger_event_type)` |
| `alerts` | `(user_id, fired_at)`, `(session_id, fired_at)` |
