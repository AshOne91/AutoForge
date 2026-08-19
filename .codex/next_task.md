# Next Task

## Next executable unit: validate an independent search consumer requirement

The default standalone profile and generated HA runtime proofs for Redis
Cluster, PostgreSQL Patroni/HAProxy, RabbitMQ, and the two-scheduler Airflow
profile are verified. The generated `service-composition.json` exposes stable
API, relay, worker, scheduler, initializer, and infrastructure roles.

Request replay/idempotency is now verified through KIS `update_profile`: two API
replicas produced one in-flight winner, a replayed response, and conflicting-key
rejection through Nginx. The first two handoffs are now bounded inside KIS:
news uses `source_key`, while operator history uses `job_id`; both rebuild safe
projections from canonical storage and use the existing hybrid transport. The
next unit is to validate an independent consumer project or an explicit
ProjectSpec requirement with the same shape before adding any AutoForge
projection generator or generic search API.
