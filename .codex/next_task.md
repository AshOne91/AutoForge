# Next Task

## Next executable unit: select a concrete S3-compatible client boundary

OWNERSHIP: AutoForge Kubernetes generator, validated through kis-auto-trading

EVIDENCE: the single-host audit confirms durable volumes, rotated logs, health
checks, bootstrap/reboot recovery, and disposable restore evidence. The identity
dump restored six public tables and both account shards restored eight public
tables each into disposable Spilo targets.

The first adapter target is the existing S3-compatible object API, backed locally
by the generated MinIO overlay and later replaceable by AWS S3 or another
compatible provider. `BackupArtifact`, `BackupTransfer`, and
`S3StorageConfig` now carry the manifest, async transfer seam, and validated
provider-neutral settings. `BackupTransfer.configuration` now exposes the
settings to an adapter. Select a client boundary next; keep scheduling and
retention policy out of this unit.
