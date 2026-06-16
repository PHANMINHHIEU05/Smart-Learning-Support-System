CREATE TABLE IF NOT EXISTS tasks (
    task_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL,
    title VARCHAR(255) NOT NULL,
    description TEXT,
    status VARCHAR(20) NOT NULL DEFAULT 'todo',
    priority INTEGER,
    due_at TIMESTAMPTZ,
    estimated_minutes INTEGER,
    subject_name VARCHAR(255),
    tags_json JSONB,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT chk_tasks_status
        CHECK (status IN ('todo', 'doing', 'done', 'archived')),
    CONSTRAINT chk_tasks_priority
        CHECK (priority IS NULL OR (priority >= 0 AND priority <= 10)),
    CONSTRAINT chk_tasks_estimated_minutes
        CHECK (estimated_minutes IS NULL OR estimated_minutes >= 1)
);

CREATE INDEX IF NOT EXISTS idx_tasks_user_id_created_at
    ON tasks (user_id, created_at DESC);

CREATE INDEX IF NOT EXISTS idx_tasks_user_id_status
    ON tasks (user_id, status);

CREATE INDEX IF NOT EXISTS idx_tasks_user_id_due_at
    ON tasks (user_id, due_at);

CREATE TABLE IF NOT EXISTS study_sessions (
    session_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL,
    task_id UUID,
    planned_mode VARCHAR(20),
    started_at TIMESTAMPTZ NOT NULL,
    ended_at TIMESTAMPTZ,
    end_reason VARCHAR(40),
    notes TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    paused_at TIMESTAMPTZ,
    pause_reason VARCHAR(80),
    CONSTRAINT chk_study_sessions_planned_mode
        CHECK (planned_mode IS NULL OR planned_mode IN ('pomodoro', 'free')),
    CONSTRAINT chk_study_sessions_end_reason
        CHECK (end_reason IS NULL OR end_reason IN ('completed', 'stopped', 'timeout', 'error')),
    CONSTRAINT chk_study_sessions_time_order
        CHECK (ended_at IS NULL OR ended_at >= started_at)
);

CREATE INDEX IF NOT EXISTS idx_study_sessions_user_id_started_at
    ON study_sessions (user_id, started_at DESC);

CREATE INDEX IF NOT EXISTS idx_study_sessions_user_id_task_id
    ON study_sessions (user_id, task_id);
