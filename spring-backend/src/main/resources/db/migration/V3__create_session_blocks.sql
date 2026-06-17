CREATE TABLE IF NOT EXISTS session_blocks (
    block_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    session_id UUID NOT NULL,
    block_type VARCHAR(20) NOT NULL,
    start_at TIMESTAMPTZ NOT NULL,
    end_at TIMESTAMPTZ,
    planned_duration_seconds INTEGER NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT chk_session_blocks_type
        CHECK (block_type IN ('focus', 'break', 'long_break')),
    CONSTRAINT chk_session_blocks_duration
        CHECK (planned_duration_seconds >= 1),
    CONSTRAINT chk_session_blocks_time_order
        CHECK (end_at IS NULL OR end_at >= start_at)
);

CREATE INDEX IF NOT EXISTS idx_session_blocks_session_id_start_at
    ON session_blocks (session_id, start_at ASC);

CREATE INDEX IF NOT EXISTS idx_session_blocks_session_id_end_at
    ON session_blocks (session_id, end_at);
