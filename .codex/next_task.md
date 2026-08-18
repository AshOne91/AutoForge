# Next Task

## Next executable unit: Control Plane PostgreSQL migration executor

OWNERSHIP: AutoForge owns ordered migration artifact discovery and the typed
version-ledger contract. The provider-owned single executor owns when and where
migrations run; Kubernetes application manifests must not execute them.

Add the smallest provider-invoked PostgreSQL executor that uses the existing
discovery and ledger contracts, serializes runs with a database advisory lock,
and executes each newly applied SQL artifact and ledger record in one database
transaction. Verify successful application and repeat-run idempotency against an
isolated PostgreSQL instance. Do not add an application-startup migration,
Kubernetes Job, PostgreSQL StatefulSet/PVC, provider SDK, CLI, retry policy,
rollback policy, or generated schema tooling in this unit.
