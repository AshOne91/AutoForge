# Next Task

## Next executable unit: define generic record-to-search handoff

The default standalone profile and generated HA runtime proofs for Redis
Cluster, PostgreSQL Patroni/HAProxy, RabbitMQ, and the two-scheduler Airflow
profile are verified. The generated `service-composition.json` exposes stable
API, relay, worker, scheduler, initializer, and infrastructure roles.

Request replay/idempotency is now verified through KIS `update_profile`: two API
replicas produced one in-flight winner, a replayed response, and conflicting-key
rejection through Nginx. The next bounded unit is the existing record-to-search
handoff item: identify one consumer-owned source record, projection identity,
and query contract while reusing the current OpenSearch/RAG transport. Do not
add a second search API or generic indexing abstraction before that slice is
bounded.
