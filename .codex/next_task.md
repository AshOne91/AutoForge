# Next Task

## Next executable unit: Control Plane provider image migration boundary

OWNERSHIP: AutoForge owns ordered migration artifact discovery and the typed
version-ledger contract. The provider-owned single executor owns when and where
migrations run; Kubernetes application manifests must not execute them.

Inspect whether the existing Control Plane container image contains both the
explicit provider CLI and declared SQL artifacts. If a small image-build change
is genuinely required, make it and verify one provider-invoked migration against
an isolated PostgreSQL instance. Do not add application-startup migration,
Kubernetes Job, PostgreSQL StatefulSet/PVC, provider SDK, retry policy, rollback
policy, or generated schema tooling in this unit.
