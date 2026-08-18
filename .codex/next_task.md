# Next Task

## Next executable unit: Control Plane Kubernetes replica continuity drill

OWNERSHIP: AutoForge owns the Control Plane HTTP/readiness contract and generated
manifest. PostgreSQL migration execution and provider runtime remain external.

Repeat the provider-backed disposable rollout, delete one Control Plane Pod, and
confirm the surviving replica and ClusterIP Service remain ready before the Pod is
recreated. Remove only the disposable resources afterward. Do not generate a
migration Job, PostgreSQL StatefulSet/PVC, dashboard, metrics backend, or agent
orchestration.
