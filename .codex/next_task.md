# Next Task

## Next executable unit: generated reporter / Control Plane interoperability test

OWNERSHIP: AutoForge owns both the generated reporter contract and the Control
Plane heartbeat API. KIS remains the consumer validation project.

Run one generated, opt-in reporter against the authenticated in-process Control
Plane heartbeat endpoint. Verify one stored payload contains the generated package
name, deployed version, normalized instance identity, and only the bounded
database/session dependency summary. Keep missing configuration and failed posts
non-fatal. Do not add a KIS manifest, Kubernetes Secret binding, sidecar,
dashboard, metrics backend, or agent orchestration.
