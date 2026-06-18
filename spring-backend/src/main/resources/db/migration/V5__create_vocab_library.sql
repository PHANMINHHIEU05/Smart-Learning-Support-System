CREATE TABLE IF NOT EXISTS vocab_library (
    vocab_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL,
    term VARCHAR(255) NOT NULL,
    meaning TEXT,
    example_sentence TEXT,
    source_type VARCHAR(40),
    source_ref TEXT,
    status VARCHAR(30) NOT NULL DEFAULT 'not_started',
    ease_factor NUMERIC(4, 2) NOT NULL DEFAULT 2.50,
    interval_days INTEGER NOT NULL DEFAULT 0,
    repetition_count INTEGER NOT NULL DEFAULT 0,
    next_review_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    last_reviewed_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT chk_vocab_library_status
        CHECK (status IN ('not_started', 'learning', 'fuzzy', 'remembered', 'mastered', 'archived')),
    CONSTRAINT chk_vocab_library_ease_factor
        CHECK (ease_factor >= 1.30 AND ease_factor <= 4.00),
    CONSTRAINT chk_vocab_library_interval_days
        CHECK (interval_days >= 0),
    CONSTRAINT chk_vocab_library_repetition_count
        CHECK (repetition_count >= 0)
);

CREATE UNIQUE INDEX IF NOT EXISTS idx_vocab_library_user_lower_term
    ON vocab_library (user_id, lower(term));

CREATE INDEX IF NOT EXISTS idx_vocab_library_user_status
    ON vocab_library (user_id, status);

CREATE INDEX IF NOT EXISTS idx_vocab_library_user_next_review
    ON vocab_library (user_id, next_review_at);
