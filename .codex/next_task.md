# Next Task

## Next executable unit: local Kubernetes generated-topology reconciliation

Use the same freshly generated KIS HA workspace to build its generated
application image and apply the generated Kubernetes base-server manifest in an
isolated Docker Desktop Kubernetes namespace. Verify the declared Nginx and
application replica counts, the internal service route, and one application Pod
replacement without changing the running lightweight Compose profile.

Do not select a cloud deployment provider, add Kubernetes migration resources,
or replace the active lightweight profile during this unit. Those are later
deployment concerns after both local Docker logical-node and local Kubernetes
topologies are reproducible.
