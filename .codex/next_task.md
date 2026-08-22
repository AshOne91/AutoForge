# Next Task

## Next executable unit: select the first consumer-owned service composition

The reusable single-host HA gate is complete: PostgreSQL, MySQL, Redis,
RabbitMQ, Airflow, application replicas, Durable Job Worker replicas, and the
intentionally single relay/message-worker recovery boundaries have recorded
local proofs. RAG, storage, inference, and observability overlays have their
separate service proofs.

The remaining Base Server map entries that are not generic infrastructure
contracts (`chat`, `data`, provider-specific external delivery) need a concrete
consumer use case before implementation. Select one KIS-owned user flow and
compose existing generated services around it; do not invent a generic domain
or repeat the completed HA drills.
