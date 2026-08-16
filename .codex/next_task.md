# Next Task

## Next executable unit: define the backup artifact manifest type

OWNERSHIP: AutoForge Kubernetes generator, validated through kis-auto-trading

EVIDENCE: the single-host audit confirms durable volumes, rotated logs, health
checks, bootstrap/reboot recovery, and disposable restore evidence. The identity
dump restored six public tables and both account shards restored eight public
tables each into disposable Spilo targets.

The first adapter target is the existing S3-compatible object API, backed locally
by the generated MinIO overlay and later replaceable by AWS S3 or another
compatible provider. Define the typed artifact manifest carrying kind, name,
size, creation time, and SHA-256 before implementing transfer code. Do not add
provider SDKs, credentials, or retention policy yet.
