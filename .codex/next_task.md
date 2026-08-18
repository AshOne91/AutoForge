# Next Task

## Next executable unit: KIS persistent local heartbeat operating check

OWNERSHIP: AutoForge owns generated reporter behavior and the Control Plane
deployment contract. KIS owns its local endpoint/token values and bootstrap
execution.

Put the optional reporter's endpoint/token in KIS's existing ignored local
environment file, run the generated Windows single-host bootstrap, and verify a
fresh report updates in the separately running Control Plane. Do not add a
sidecar, dashboard, metrics backend, or agent orchestration.
