# Next Task

## Next executable unit: verify Redis restart recovery in the isolated profile

Extend the existing isolated single-host verifier after its PostgreSQL recovery
proof: restart the standalone Redis service, wait for its health and the
application replicas' readiness, then repeat one Transactional Outbox
notification smoke. This checks reconnect behavior for sessions and the Redis
Pub/Sub backplane without claiming Redis HA or failover.

Keep the stack disposable and do not add acknowledgement, replay, rate-limit,
or external-delivery policy.
