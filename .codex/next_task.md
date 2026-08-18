# Next Task

## Next executable unit: Control Plane migration artifact discovery

OWNERSHIP: AutoForge owns ordered migration artifact discovery and the typed
version-ledger contract. The provider-owned single executor owns when and where
migrations run; Kubernetes application manifests must not execute them.

Add the smallest filesystem discovery function that reads declared SQL artifacts,
derives their immutable checksums, and returns the existing ordered contract.
Reject malformed versioned filenames and duplicate versions with focused tests.
Do not add an executor, application-startup migration, Kubernetes Job,
PostgreSQL StatefulSet/PVC, provider SDK, advisory-lock orchestration, retry
policy, rollback policy, or schema tooling in this unit.
