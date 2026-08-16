# Next Task

## Next executable unit: validate the actual KIS single-host preflight

OWNERSHIP: KIS operator configuration and AutoForge-generated single-host
artifacts

EVIDENCE: the single-host audit confirms durable volumes, rotated logs, health
checks, bootstrap/reboot recovery, and disposable restore evidence. The identity
dump restored six public tables and both account shards restored eight public
tables each into disposable Spilo targets.

The default generated MinIO overlay remains profile-selected at execution. Its
generated `minio-init` task creates `S3_BUCKET` idempotently, and a disposable
KIS consumer workspace passed the actual `autoforge backup` preflight. The KIS
generated README conflict is resolved without overwriting KIS-owned operations
documentation. PostgreSQL HA remains the selected runtime; MySQL is deferred
until a real consumer requirement exists.

Run the read-only KIS `validate-ports` command against every active Compose
environment file, then inspect the resolved single-host Compose configuration.
Only after those checks are clean, decide whether an actual container restart
or backup drill is needed. Do not change database providers, add scheduling,
or introduce new infrastructure in this unit.
