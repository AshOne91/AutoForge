# Next Task

## Next executable unit: verify PostgreSQL restart recovery in the isolated profile

Extend the existing isolated single-host verifier after its outbox/relay/worker
proof: restart the volume-backed PostgreSQL service, wait for its health and the
generated application replicas' readiness, then repeat one Transactional Outbox
notification smoke. This checks existing connection recovery and durable volume
behavior without claiming database HA.

Keep the stack disposable and do not add acknowledgement, replay, rate-limit,
or external-delivery policy.
