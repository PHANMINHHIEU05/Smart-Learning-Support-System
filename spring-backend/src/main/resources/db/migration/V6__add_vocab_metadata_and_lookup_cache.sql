ALTER TABLE vocab_library
    ADD COLUMN IF NOT EXISTS translation_vi TEXT,
    ADD COLUMN IF NOT EXISTS definition_en TEXT,
    ADD COLUMN IF NOT EXISTS part_of_speech VARCHAR(80),
    ADD COLUMN IF NOT EXISTS phonetic VARCHAR(255),
    ADD COLUMN IF NOT EXISTS audio_url TEXT,
    ADD COLUMN IF NOT EXISTS dictionary_provider VARCHAR(100),
    ADD COLUMN IF NOT EXISTS translation_provider VARCHAR(100);

CREATE TABLE IF NOT EXISTS vocab_lookup_cache (
    normalized_term VARCHAR(255) PRIMARY KEY,
    term VARCHAR(255) NOT NULL,
    meaning TEXT,
    translation_vi TEXT,
    definition_en TEXT,
    example_sentence TEXT,
    part_of_speech VARCHAR(80),
    phonetic VARCHAR(255),
    audio_url TEXT,
    dictionary_provider VARCHAR(100),
    translation_provider VARCHAR(100),
    fetched_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    expires_at TIMESTAMPTZ NOT NULL,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_vocab_lookup_cache_expires_at
    ON vocab_lookup_cache (expires_at);
