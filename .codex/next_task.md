# Next Task

## Next executable unit: KIS heartbeat failure-containment drill

OWNERSHIP: AutoForge owns generated reporter behavior and the Control Plane
deployment contract. KIS owns its local endpoint/token values and bootstrap
execution; no generated KIS output may be patched directly.

Temporarily use an invalid local Control Plane token, run the generated Windows
single-host bootstrap, and verify that KIS remains healthy while the reporter
does not create a new accepted report. Restore the valid ignored local token,
rerun bootstrap, and verify a fresh report returns. Do not add a sidecar,
dashboard, metrics backend, or agent orchestration.
