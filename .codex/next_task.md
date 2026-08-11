# Next Task

## Scheduled Ingestion Blueprint runtime validation

The `identity_session_profile` Blueprint is complete: its generated Docker
image, PostgreSQL, Redis Cluster, migration, and FastAPI `/health` endpoint
have been validated in an isolated Compose project.

The `scheduled_ingestion` Blueprint is also complete at the generator level:

- its `autoforge generate` command validates the generated project;
- Docker Compose configuration renders with all variables resolved;
- it generates PostgreSQL, RabbitMQ, Airflow, application, migration, outbox
  relay, and durable-job worker services;
- its external API adapter and durable-job business handler remain scaffolded
  and consumer-owned.

## Next bounded contract

Run the generated `scheduled_ingestion` environment as an isolated Docker
Compose project. Verify only infrastructure-owned behavior:

1. PostgreSQL, RabbitMQ, migration, and application become healthy.
2. Airflow registers the generated DAG without import errors.
3. The private durable-job API rejects an unauthenticated request.
4. An authenticated request creates a durable job and the outbox/worker path
   reaches the expected terminal state when the scaffolded handler is absent.

Do not add KIS API calls, news parsing, RAG indexing, trading logic, cloud
deployment, Kubernetes, or a WebSocket generator in this step.

## Why this is next

The `realtime` Blueprint remains a later direction. Current AutoForge has no
WebSocket generation contract, and no KIS consumer requirement has selected
one. Adding metadata or an empty generator now would create speculative
architecture rather than a validated reusable contract.

## Constraints

- Preserve Generator, GenerationPlan, Manifest, and ownership contracts.
- Treat generated service files as AutoForge-owned.
- Treat the durable-job business handler and external API adapter as
  scaffolded, consumer-owned code.
- Use the smallest focused tests before broader validation.
- Use an isolated Compose project and remove its temporary output after
  validation; do not alter running KIS containers.
