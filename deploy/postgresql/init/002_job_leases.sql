ALTER TABLE autoforge_generation_jobs
    ADD COLUMN IF NOT EXISTS lease_owner VARCHAR(255),
    ADD COLUMN IF NOT EXISTS lease_token VARCHAR(128),
    ADD COLUMN IF NOT EXISTS lease_expires_at TIMESTAMPTZ,
    ADD COLUMN IF NOT EXISTS heartbeat_at TIMESTAMPTZ;

CREATE INDEX IF NOT EXISTS ix_autoforge_generation_jobs_claimable
    ON autoforge_generation_jobs (status, lease_expires_at, created_at);

ALTER TABLE autoforge_generation_jobs
    DROP CONSTRAINT IF EXISTS ck_autoforge_generation_jobs_lease_complete;

ALTER TABLE autoforge_generation_jobs
    ADD CONSTRAINT ck_autoforge_generation_jobs_lease_complete CHECK (
        (lease_owner IS NULL AND lease_token IS NULL
            AND lease_expires_at IS NULL AND heartbeat_at IS NULL)
        OR
        (lease_owner IS NOT NULL AND lease_token IS NOT NULL
            AND lease_expires_at IS NOT NULL AND heartbeat_at IS NOT NULL)
    );
