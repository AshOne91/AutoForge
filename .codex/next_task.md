# Next Task

## Next executable unit: Control Plane provider migration CLI

OWNERSHIP: AutoForge owns ordered migration artifact discovery and the typed
version-ledger contract. The provider-owned single executor owns when and where
migrations run; Kubernetes application manifests must not execute them.

Add one explicit provider-facing CLI command that resolves a database URL and
migration directory, runs the existing PostgreSQL executor, and emits only the
applied migration versions. Verify a subprocess against an isolated PostgreSQL
instance. Do not invoke it from application startup, Kubernetes Job,
PostgreSQL StatefulSet/PVC, provider SDK, retry policy, rollback policy, or
generated schema tooling in this unit.
