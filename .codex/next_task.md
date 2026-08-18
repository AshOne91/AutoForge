# Next Task

## Next executable unit: Control Plane Kubernetes manifest validation

OWNERSHIP: AutoForge owns the Control Plane specification and generated manifest.
PostgreSQL migration execution and cluster runtime remain provider-owned.

Validate the generated Control Plane manifest against the available Kubernetes
client/schema tooling and, when a cluster is available, perform a disposable
apply/rollout probe. Keep it separate from consumer `base-server.yaml`. Do not
generate a migration Job, PostgreSQL StatefulSet/PVC, dashboard, metrics backend,
or agent orchestration.
