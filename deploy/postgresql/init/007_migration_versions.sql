CREATE TABLE IF NOT EXISTS autoforge_migration_versions (
    version INTEGER PRIMARY KEY CHECK (version > 0),
    path VARCHAR(512) NOT NULL,
    checksum CHAR(64) NOT NULL,
    applied_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CHECK (checksum ~ '^[0-9a-f]{64}$')
);

INSERT INTO autoforge_migration_versions (version, path, checksum)
VALUES
    (1, '001_control_plane.sql', '747eec5a1b6054184699996917bf6a2770981aa8d8f46cb24d1b83cbd5e043a4'),
    (2, '002_job_leases.sql', '8c9d7ce905ddaec14f2c23bf6111d67b288d27937dd6e822a1c4dfea3e0258d2'),
    (3, '003_job_committing_status.sql', 'fb6e2a004b9df7f84db9758cdf2e222b09f34ac823de4dd770296f50fae0e91a'),
    (4, '004_job_pushing_status.sql', 'b15f3c060bae25bb5d30cf7b7c7d0c738fe08a3e2993412e008a3a3b6c529706'),
    (5, '005_job_opening_pull_request_status.sql', '314dc6e8bfcf598e4d0b2eb633364a9972659e86beb6e1761f85f0616e79edfa'),
    (6, '006_service_heartbeats.sql', '4a7bf5a3bbc9c7283200480b1bd448c5776a26911f1514df7b96c2c6cacd4e70')
ON CONFLICT (version) DO NOTHING;
