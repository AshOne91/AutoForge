# Next Task

## Next executable unit: Provider-backed Control Plane readiness validation

OWNERSHIP: AutoForge owns the Control Plane HTTP/readiness contract and generated
manifest. PostgreSQL migration execution and provider runtime remain external.

Repeat the disposable Kubernetes rollout with a provider-owned PostgreSQL endpoint
whose schema has migrations `001`–`006` applied. Confirm both replicas become
ready, then remove only the disposable resources. Do not generate a migration Job,
PostgreSQL StatefulSet/PVC, dashboard, metrics backend, or agent orchestration.
