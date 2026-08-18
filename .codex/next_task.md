# Next Task

## Next executable unit: Control Plane Kubernetes runtime validation

OWNERSHIP: AutoForge owns the Control Plane specification and generated manifest.
PostgreSQL migration execution and cluster runtime remain provider-owned.

When an accessible Kubernetes API server and kubeconfig are available, perform a
disposable apply/rollout probe for the generated Control Plane manifest. Until
then, the YAML/generator tests are the validation boundary. Keep it separate from
consumer `base-server.yaml`. Do not generate a migration Job, PostgreSQL
StatefulSet/PVC, dashboard, metrics backend, or agent orchestration.
