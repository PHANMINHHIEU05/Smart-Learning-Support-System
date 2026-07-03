ALTER TABLE vocab_library
    ADD COLUMN IF NOT EXISTS collocation TEXT,
    ADD COLUMN IF NOT EXISTS study_box INTEGER NOT NULL DEFAULT 1;

ALTER TABLE vocab_library
    DROP CONSTRAINT IF EXISTS chk_vocab_library_study_box;

ALTER TABLE vocab_library
    ADD CONSTRAINT chk_vocab_library_study_box
        CHECK (study_box >= 1 AND study_box <= 3);
