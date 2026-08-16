# Next Task

## Next executable unit: implement the MySQL standalone Compose generator

OWNERSHIP: AutoForge local database runtime generator, validated through a
generated consumer project

EVIDENCE: the single-host audit confirms durable volumes, rotated logs, health
checks, bootstrap/reboot recovery, and disposable restore evidence. The identity
dump restored six public tables and both account shards restored eight public
tables each into disposable Spilo targets.

The default generated MinIO overlay remains profile-selected at execution. Its
generated `minio-init` task creates `S3_BUCKET` idempotently, and a disposable
KIS consumer workspace passed the actual `autoforge backup` preflight. The KIS
generated README conflict is resolved without overwriting KIS-owned operations
documentation.

Implement the existing MySQL admission gate as one vertical slice: standalone
Compose service, explicit `mysql+asyncmy` UTF-8 DSN, health check, initialized
logical databases, MySQL-specific Alembic baseline, and disposable migration/
schema validation. Do not accept `mysql` in `ProjectSpec` before this complete
slice passes.
