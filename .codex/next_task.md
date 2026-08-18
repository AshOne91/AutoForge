# Next Task

## Next executable unit: Kubernetes-native Control Plane manifest contract

OWNERSHIP: AutoForge owns the generated Control Plane Deployment, Service, Secret
binding, and probe contract. PostgreSQL migration execution remains provider-owned.

Define the generated Kubernetes-native resource contract using the selected
Secret keys, private ClusterIP Service, `/health` liveness, and `/readiness`
readiness. Do not generate a migration Job, PostgreSQL StatefulSet/PVC, dashboard,
metrics backend, or agent orchestration.
