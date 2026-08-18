# Next Task

## Next executable unit: Control Plane Kubernetes specification profile

OWNERSHIP: AutoForge owns the Control Plane specification and generated manifest.
PostgreSQL migration execution remains provider-owned.

Add the smallest opt-in specification profile and generator output for the
documented Deployment, private ClusterIP Service, Secret references, and probes.
Keep it separate from the consumer `base-server.yaml` output. Do not generate a
migration Job, PostgreSQL StatefulSet/PVC, dashboard, metrics backend, or agent
orchestration.
