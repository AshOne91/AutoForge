# Next Task

## Next executable unit: connect generated S3 settings to the backup runtime

OWNERSHIP: AutoForge storage generator and backup configuration boundary,
validated through a generated consumer project

EVIDENCE: the single-host audit confirms durable volumes, rotated logs, health
checks, bootstrap/reboot recovery, and disposable restore evidence. The identity
dump restored six public tables and both account shards restored eight public
tables each into disposable Spilo targets.

The default generated MinIO overlay remains profile-selected at execution. Its
generated `minio-init` task creates `S3_BUCKET` idempotently, and a disposable
MinIO backup round trip passed against the generated Compose output.

Add the smallest generated runtime handoff that maps `S3_ENDPOINT_URL`,
`S3_BUCKET`, `S3_PREFIX`, and credential reference names to `S3StorageConfig`
without placing secret values in a generated application module. Validate the
generated configuration against the existing S3 backup adapter. Keep MySQL
behind its existing standalone admission gate; do not accept `mysql` as a spec
value before that complete slice is implemented.
