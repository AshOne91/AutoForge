# Next Task

## Next executable unit: KIS durable-job worker through RabbitMQ cluster

OWNERSHIP: AutoForge local-environment generator; KIS consumer specification
and generated durable-job worker.

Start the existing generated durable-job worker against the verified local
RabbitMQ cluster. Submit one existing Durable Job through its public API and
verify worker claim, completion, and status retrieval through the HAProxy
broker endpoint. Do not add a new job type or modify user-owned job handlers
unless this runtime check proves a concrete generator or runtime defect.
