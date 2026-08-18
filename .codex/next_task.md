# Next Task

## Next executable unit: Control Plane heartbeat write continuity through replica loss

OWNERSHIP: AutoForge owns the Control Plane HTTP/readiness contract and generated
manifest. PostgreSQL migration execution and provider runtime remain external.

Using a provider-backed disposable database, record a generated KIS service
heartbeat through the internal Control Plane ClusterIP, delete one exact Control
Plane Pod, then record a second distinct generated heartbeat through the same
ClusterIP. Confirm both authenticated records remain queryable while the
Deployment replaces the deleted Pod. Remove only disposable resources afterward.
Do not generate a migration Job, PostgreSQL StatefulSet/PVC, dashboard, metrics
backend, or agent orchestration.
