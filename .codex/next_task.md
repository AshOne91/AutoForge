# Next Task

## Next executable unit: generated service-heartbeat reporter design slice

OWNERSHIP: AutoForge generated runtime contract and Control Plane heartbeat API;
KIS is the consumer validation project.

Design the smallest generated service reporter that can post its instance
identity, deployed version, and bounded dependency summary to the implemented
Control Plane API. Reuse existing generated configuration and application
lifespan boundaries. Keep reporting opt-in and do not add a sidecar, dashboard,
metrics backend, or agent orchestration before a real KIS runtime path selects
the feature.
