# Next Task

## Next executable unit: Control Plane DB-aware readiness contract

OWNERSHIP: AutoForge owns Control Plane HTTP health semantics. PostgreSQL
availability remains a provider-owned dependency.

Add a dedicated readiness endpoint that verifies the configured Control Plane
store is usable without changing `/health` process-liveness semantics. Cover a
ready store and an unavailable store with focused HTTP tests. Do not generate a
Kubernetes manifest yet, and do not add a sidecar, dashboard, metrics backend,
or agent orchestration.
