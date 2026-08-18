CREATE TABLE IF NOT EXISTS autoforge_migration_versions (
    version INTEGER PRIMARY KEY CHECK (version > 0),
    path VARCHAR(512) NOT NULL,
    checksum CHAR(64) NOT NULL,
    applied_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CHECK (checksum ~ '^[0-9a-f]{64}$')
);
