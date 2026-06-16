CREATE EXTENSION IF NOT EXISTS pgcrypto;

CREATE TABLE IF NOT EXISTS system_logs (
    log_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    source_service VARCHAR(100) NOT NULL,
    severity VARCHAR(20) NOT NULL,
    category VARCHAR(40) NOT NULL,
    message VARCHAR(2000) NOT NULL,
    correlation_id VARCHAR(120),
    payload_json JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_system_logs_created_at
    ON system_logs (created_at DESC);

CREATE INDEX IF NOT EXISTS idx_system_logs_source_service
    ON system_logs (source_service);

CREATE INDEX IF NOT EXISTS idx_system_logs_severity
    ON system_logs (severity);

CREATE INDEX IF NOT EXISTS idx_system_logs_category
    ON system_logs (category);
