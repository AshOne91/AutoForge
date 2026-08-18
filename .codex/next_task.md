# Next Task

## Next executable unit: Control Plane initialization-path reconciliation

OWNERSHIP: AutoForge owns the local Compose bootstrap configuration, ordered
migration artifacts, and the durable version-ledger contract. A provider owns
when and where the explicit executor runs; Kubernetes application manifests
must not execute migrations.

Establish one safe ownership boundary for a new empty Control Plane database:
either Docker-entrypoint initialization records durable version evidence, or the
provider CLI is the only artifact executor. Prove the chosen path against the
existing Compose profile without reapplying schema SQL to a bootstrap-initialized
database. Do not add application-startup migration, Kubernetes Job, PostgreSQL
StatefulSet/PVC, provider SDK, retry policy, rollback policy, or generated schema
tooling in this unit.
