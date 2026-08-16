# Next Task

## Next executable unit: implement the MySQL standalone Compose generator

OWNERSHIP: AutoForge Kubernetes generator, validated through kis-auto-trading

EVIDENCE: the single-host audit confirms durable volumes, rotated logs, health
checks, bootstrap/reboot recovery, and disposable restore evidence. The identity
dump restored six public tables and both account shards restored eight public
tables each into disposable Spilo targets.

The default generated MinIO overlay remains profile-selected at execution, and
its backup integration check now has passing disposable-container evidence.
`tooling.local_environment.database_provider` now owns runtime selection and
defaults to PostgreSQL, separately from provider-agnostic schema specification.
The MySQL standalone admission gate is defined: Compose, `asyncmy` DSN/secret
boundary, MySQL-specific migration baseline, health check, and disposable
validation must land together. Implement the isolated Compose generator path
next; do not accept `mysql` as a spec value before that slice is complete.
