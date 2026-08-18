# Next Task

## Next executable unit: Control Plane provider migration CLI failure containment

OWNERSHIP: AutoForge owns ordered migration artifact discovery and the typed
version-ledger contract. The provider-owned single executor owns when and where
migrations run; Kubernetes application manifests must not execute them.

Run the provider CLI in an isolated PostgreSQL subprocess scenario with a
deliberately invalid SQL artifact. Confirm a nonzero exit, no database URL or SQL
text in output, no ledger evidence, and no partially created database object.
Do not add application-startup migration, Kubernetes Job, PostgreSQL
StatefulSet/PVC, provider SDK, retry policy, rollback policy, or generated schema
tooling in this unit.
