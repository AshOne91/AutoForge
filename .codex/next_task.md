# Next Task

## Next executable unit: define off-host backup boundary

OWNERSHIP: AutoForge Kubernetes generator, validated through kis-auto-trading

EVIDENCE: the single-host audit confirms durable volumes, rotated logs, health
checks, bootstrap/reboot recovery, and disposable restore evidence. The identity
dump restored six public tables and both account shards restored eight public
tables each into disposable Spilo targets.

Define the smallest provider-neutral boundary for copying verified dumps and
logs off-host, including retention and restore ownership. Do not add a cloud
provider or schedule until that contract is explicit.
