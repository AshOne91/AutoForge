# Next Task

## Next executable unit: validate generated backup preflight in a consumer

OWNERSHIP: AutoForge backup runtime boundary, validated through a generated
consumer project

EVIDENCE: the single-host audit confirms durable volumes, rotated logs, health
checks, bootstrap/reboot recovery, and disposable restore evidence. The identity
dump restored six public tables and both account shards restored eight public
tables each into disposable Spilo targets.

The default generated MinIO overlay remains profile-selected at execution. Its
generated `minio-init` task creates `S3_BUCKET` idempotently, and a disposable
MinIO backup round trip passed against the generated Compose output.

The `autoforge backup` preflight now loads the generated `S3_*` settings,
resolves credentials through `EnvironmentSecretProvider`, and performs one
manifest transfer/verification using the existing backup adapter. Validate
that command against one generated consumer and its disposable MinIO profile.
Do not add scheduling, retention, cloud credentials, or application-specific
backup policy in this slice. Keep MySQL behind its existing standalone
admission gate; do not accept `mysql` as a spec value before that complete
slice is implemented.
