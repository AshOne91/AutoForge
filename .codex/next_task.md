# Next Task

## Next executable unit: run the MinIO integration check in a real profile

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
settings to an adapter, while the core remains SDK-neutral. Implement one
infrastructure adapter with an injected async S3-compatible client; that adapter
now exists and is tested. `aioboto3` is selected through the optional `backup`
extra, and its lifecycle-safe wrapper is implemented. Add only a disposable
MinIO integration check next; the check now exists and skips when its required
environment is absent. Run it against the generated storage profile; keep upload
scheduling and retention policy out of this unit.
