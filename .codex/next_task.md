# Next Task

## Next executable unit: Control Plane PostgreSQL migration-ledger adapter

OWNERSHIP: AutoForge owns ordered migration artifact discovery and the typed
version-ledger contract. The provider-owned single executor owns when and where
migrations run; Kubernetes application manifests must not execute them.

Add the smallest PostgreSQL infrastructure adapter for the existing
`MigrationVersionLedger` contract and its explicit SQL table. Verify persisted
applied-version read/write behavior with the existing isolated PostgreSQL test
pattern. Do not add an executor, application-startup migration, Kubernetes Job,
PostgreSQL StatefulSet/PVC, provider SDK, advisory-lock orchestration, retry
policy, rollback policy, or schema tooling in this unit.
