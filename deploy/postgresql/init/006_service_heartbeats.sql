CREATE TABLE IF NOT EXISTS autoforge_service_heartbeats (
    service_name VARCHAR(128) NOT NULL,
    instance_id VARCHAR(128) NOT NULL,
    deployed_version VARCHAR(128) NOT NULL,
    dependency_summary JSONB NOT NULL DEFAULT '{}'::jsonb,
    reported_at TIMESTAMPTZ NOT NULL,
    expires_at TIMESTAMPTZ NOT NULL,
    PRIMARY KEY (service_name, instance_id),
    CHECK (expires_at > reported_at)
);

CREATE INDEX IF NOT EXISTS ix_autoforge_service_heartbeats_expires_at
    ON autoforge_service_heartbeats (expires_at);
