# Next Task

## Next executable unit: resolve the KIS generated README ownership conflict

OWNERSHIP: AutoForge single-host documentation generator and KIS user-owned
operations documentation

EVIDENCE: the single-host audit confirms durable volumes, rotated logs, health
checks, bootstrap/reboot recovery, and disposable restore evidence. The identity
dump restored six public tables and both account shards restored eight public
tables each into disposable Spilo targets.

The default generated MinIO overlay remains profile-selected at execution. Its
generated `minio-init` task creates `S3_BUCKET` idempotently, and a disposable
KIS consumer workspace passed the actual `autoforge backup` preflight.

KIS `deploy/single-host/README.md` is marked GENERATED but contains manual
port and backup-drill content, so safe regeneration correctly aborts. Preserve
the KIS-specific drill in its existing user-owned operations document, move any
reusable operating contract into the AutoForge single-host generator, then
regenerate and inspect the KIS diff. Do not force overwrite the generated file.
