# Next Task

## Next executable unit: Control Plane service-heartbeat contract slice

OWNERSHIP: AutoForge Control Plane and generated service runtime; KIS is the
consumer validation project.

Introduce the smallest authenticated, expiring heartbeat contract for a running
service identity, deployed version, and bounded dependency summary. Keep
generated Compose/Kubernetes pull probes as the routing and restart authority,
and keep public synthetic probes external. Start with one storage/API vertical
slice; do not add a dashboard, a new metrics backend, or agent orchestration.
