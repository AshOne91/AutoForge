# Next Task

## Next executable unit: verify idempotency under multi-replica contention

The default standalone profile and the generated HA runtime proofs for Redis
Cluster, PostgreSQL Patroni/HAProxy, RabbitMQ, and the two-scheduler Airflow
profile are verified. The generated `service-composition.json` now exposes
stable API, relay, worker, scheduler, initializer, and infrastructure roles
without changing service names or runtime behavior. The next bounded unit is
the existing roadmap item for request replay/idempotency: define one
consumer-facing claim/replay boundary on top of the current Redis session and
Durable Job contracts. Keep the slice narrow; do not duplicate Durable Job
idempotency or introduce a generic distributed lock. Use the existing KIS HA
profile and two API replicas; prove one winner, one replayed response, and
conflicting-key rejection through the generated route. If the live contention
drill is blocked by an unavailable Redis profile, report the environment
failure instead of weakening the contract.
