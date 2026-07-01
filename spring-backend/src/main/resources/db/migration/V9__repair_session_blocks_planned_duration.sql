ALTER TABLE session_blocks
    ADD COLUMN IF NOT EXISTS planned_duration_seconds INTEGER NOT NULL DEFAULT 1500;

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1
        FROM pg_constraint
        WHERE conname = 'chk_session_blocks_duration'
          AND conrelid = 'session_blocks'::regclass
    ) THEN
        ALTER TABLE session_blocks
            ADD CONSTRAINT chk_session_blocks_duration
                CHECK (planned_duration_seconds >= 1)
                NOT VALID;
    END IF;
END $$;

ALTER TABLE session_blocks
    VALIDATE CONSTRAINT chk_session_blocks_duration;
