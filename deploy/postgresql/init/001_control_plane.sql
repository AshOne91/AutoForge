CREATE TABLE IF NOT EXISTS autoforge_generation_jobs (
    job_id VARCHAR(128) PRIMARY KEY,
    idempotency_key VARCHAR(255) UNIQUE,
    status VARCHAR(32) NOT NULL CHECK (
        status IN ('pending', 'generating', 'validating', 'succeeded', 'failed')
    ),
    document JSONB NOT NULL,
    revision INTEGER NOT NULL DEFAULT 0 CHECK (revision >= 0),
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS ix_autoforge_generation_jobs_status
    ON autoforge_generation_jobs (status);

CREATE TABLE IF NOT EXISTS autoforge_audit_records (
    event_id VARCHAR(128) PRIMARY KEY,
    event_type VARCHAR(255) NOT NULL,
    event_version VARCHAR(32) NOT NULL,
    event_created_at TIMESTAMPTZ NOT NULL,
    correlation_id VARCHAR(128),
    causation_id VARCHAR(128),
    job_id VARCHAR(128),
    producer VARCHAR(255),
    recorded_at TIMESTAMPTZ NOT NULL,
    payload_redaction TEXT NOT NULL DEFAULT 'envelope_only'
        CHECK (payload_redaction = 'envelope_only')
);

CREATE INDEX IF NOT EXISTS ix_autoforge_audit_records_event_type
    ON autoforge_audit_records (event_type);
CREATE INDEX IF NOT EXISTS ix_autoforge_audit_records_correlation_id
    ON autoforge_audit_records (correlation_id);
CREATE INDEX IF NOT EXISTS ix_autoforge_audit_records_job_id
    ON autoforge_audit_records (job_id);
