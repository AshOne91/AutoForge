# Next Task

## Next executable unit: Select Kubernetes Control Plane deployment provider

OWNERSHIP: AutoForge owns the Control Plane and generated heartbeat contracts;
the deployment provider owns Secret injection and endpoint exposure.

Compare the existing Docker profile with one provider-selected Kubernetes
deployment contract for the Control Plane: Secret binding, private PostgreSQL
dependency, health/readiness behavior, and an external synthetic probe. Choose
the provider before adding manifests or generator output. Do not add a sidecar,
dashboard, metrics backend, or agent orchestration.
