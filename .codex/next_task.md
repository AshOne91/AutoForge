# Next Task

## Next executable unit: choose the off-host backup adapter boundary

OWNERSHIP: AutoForge Kubernetes generator, validated through kis-auto-trading

EVIDENCE: the single-host audit confirms durable volumes, rotated logs, health
checks, bootstrap/reboot recovery, and disposable restore evidence. The identity
dump restored six public tables and both account shards restored eight public
tables each into disposable Spilo targets.

The provider-neutral boundary is now documented: AutoForge owns verified dump/
log artifact shape and restore evidence; an operator or provider adapter owns
transfer, encryption, retention, and deletion. Select the next adapter contract
without adding a cloud provider, credentials, or schedule yet.
