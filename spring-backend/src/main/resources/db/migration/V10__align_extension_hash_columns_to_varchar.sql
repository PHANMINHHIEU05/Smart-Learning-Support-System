ALTER TABLE vocab_extension_pairing_codes
    ALTER COLUMN code_hash TYPE VARCHAR(64);

ALTER TABLE vocab_extension_sessions
    ALTER COLUMN token_hash TYPE VARCHAR(64);
