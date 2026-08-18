# Next Task

## Next executable unit: durable Redis primary-failover verifier

Confirm the ownership of the existing KIS generated-runtime verification
scripts. If they are user-owned, extend the closest existing verifier to reuse
its isolated Compose lifecycle and Redis topology helpers for the already-proven
session-key primary failover path: promotion, all-slot health, generated
multi-startup-node session read, and stopped-node rejoin. Do not hand-edit
generated Compose artifacts, replace the lightweight profile, or change the
AutoForge generator unless the durable verifier exposes a new generated-output
defect.

Do not select a cloud deployment provider or add Kubernetes stateful-provider
resources during this unit. Kubernetes provider-store connectivity remains a
later concern after this Docker logical-node failure check is reproducible by a
checked-in operational verifier.
