# Next Task

## Next executable unit: Control Plane heartbeat interoperability in Kubernetes

OWNERSHIP: AutoForge owns the Control Plane HTTP/readiness contract and generated
manifest. PostgreSQL migration execution and provider runtime remain external.

Run the generated service-heartbeat reporter against the internal Control Plane
ClusterIP using the provider-backed disposable database. Confirm authenticated
upsert/query behavior while keeping the Control Plane replicas stateless. Remove
only disposable resources afterward. Do not generate a migration Job, PostgreSQL
StatefulSet/PVC, dashboard, metrics backend, or agent orchestration.
