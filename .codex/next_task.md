# Next Task

## Next executable unit: validate a second record-to-search consumer

The default standalone profile and generated HA runtime proofs for Redis
Cluster, PostgreSQL Patroni/HAProxy, RabbitMQ, and the two-scheduler Airflow
profile are verified. The generated `service-composition.json` exposes stable
API, relay, worker, scheduler, initializer, and infrastructure roles.

Request replay/idempotency is now verified through KIS `update_profile`: two API
replicas produced one in-flight winner, a replayed response, and conflicting-key
rejection through Nginx. The first record-to-search handoff is also bounded by
the KIS news flow: `source_key` crosses the durable job, the consumer rebuilds
the projection from canonical storage, and the existing hybrid transport serves
queries. The next unit is to validate one independent consumer with the same
shape before adding any AutoForge projection generator or generic search API.
