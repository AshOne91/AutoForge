# Next Task

## Next executable unit: Control Plane migration operating contract

OWNERSHIP: AutoForge owns Control Plane deployment sequencing and migration
documentation. PostgreSQL remains a provider-owned dependency.

Define the idempotent, versioned migration execution contract required before a
Kubernetes-native Control Plane manifest can be generated. Reuse the existing
SQL migration ordering; do not generate the manifest yet, and do not add a
sidecar, dashboard, metrics backend, or agent orchestration.
