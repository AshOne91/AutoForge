# Next Task

## Next executable unit: Control Plane heartbeat deployment profile

OWNERSHIP: AutoForge owns the Control Plane deployment contract and generated
heartbeat configuration. KIS remains the consumer validation project.

Define one minimal deployment profile for the existing authenticated heartbeat
intake and its PostgreSQL persistence. Bind the reporter endpoint and token only
through the selected deployment secret mechanism, preserve Pull probes as the
routing/restart authority, and validate one disposable runtime path before opting
KIS in. Do not add a sidecar, dashboard, metrics backend, or agent orchestration.
