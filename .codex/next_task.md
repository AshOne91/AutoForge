# Next Task

## Next executable unit: Control Plane legacy bootstrap-volume policy

OWNERSHIP: AutoForge owns the ordered migration artifacts and durable
version-ledger contract. An operator owns whether a prior local Compose volume
is retained, backed up, reset, or explicitly reconciled; application manifests
must not execute migrations.

Define and verify the safe operator procedure for a named volume created by the
former Docker-entrypoint SQL bootstrap: detect the missing ledger evidence,
preserve data, and make the supported recovery choice explicit. Do not
automatically reapply schema SQL, mutate a legacy volume, add application-startup
migration, Kubernetes Job, PostgreSQL StatefulSet/PVC, provider SDK, retry
policy, rollback policy, or generated schema tooling in this unit.
