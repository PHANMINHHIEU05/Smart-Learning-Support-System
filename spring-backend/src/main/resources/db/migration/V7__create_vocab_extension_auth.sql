CREATE TABLE IF NOT EXISTS vocab_extension_pairing_codes (
    pairing_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    code_hash CHAR(64) NOT NULL UNIQUE,
    user_id UUID NOT NULL,
    expires_at TIMESTAMPTZ NOT NULL,
    consumed_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_vocab_extension_pairing_codes_user_created
    ON vocab_extension_pairing_codes (user_id, created_at DESC);

CREATE INDEX IF NOT EXISTS idx_vocab_extension_pairing_codes_expires
    ON vocab_extension_pairing_codes (expires_at);

CREATE TABLE IF NOT EXISTS vocab_extension_sessions (
    session_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    token_hash CHAR(64) NOT NULL UNIQUE,
    user_id UUID NOT NULL,
    device_label VARCHAR(120),
    last_used_at TIMESTAMPTZ,
    expires_at TIMESTAMPTZ NOT NULL,
    revoked_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_vocab_extension_sessions_user_created
    ON vocab_extension_sessions (user_id, created_at DESC);

CREATE INDEX IF NOT EXISTS idx_vocab_extension_sessions_active
    ON vocab_extension_sessions (token_hash, expires_at)
    WHERE revoked_at IS NULL;
