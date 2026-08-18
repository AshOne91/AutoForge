# Next Task

## Next executable unit: KIS local heartbeat opt-in validation

OWNERSHIP: AutoForge owns generated reporter behavior and the Control Plane
deployment contract. KIS owns selection of the optional reporter in its project
specification and local secret values.

Select the optional reporter in KIS's user-owned project specification, regenerate
only generated-owned output, and point the local application to the separately
started Control Plane profile through its endpoint/token environment contract.
Verify one KIS report persists in Control Plane without exposing credentials in
Git. Do not add a sidecar, dashboard, metrics backend, or agent orchestration.
