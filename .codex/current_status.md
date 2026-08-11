# Current Status

## Stable foundation

AutoForge currently has working foundations for:

- specification and generation contracts
- manifest and file ownership
- isolated workspaces
- validation/build pipeline
- generator and validator plugins
- PostgreSQL-oriented database generation
- Redis and RabbitMQ integration foundations
- Transactional Outbox
- EventBus and ordered Pipeline execution
- durable GenerationJob processing
- PostgreSQL JobStore and worker leasing
- isolated Git checkout
- safe branch/commit/push/Pull Request automation
- authenticated Control Plane API
- persistent worker/server entry points
- GitHub webhook verification and delivery deduplication
- GitHub Actions/Jenkins validation configuration generation
- generated Dockerfile and local/integration Compose environments
- PostgreSQL, Redis Cluster, RabbitMQ, migration, application, Airflow, Outbox relay,
  and durable-job worker runtime validation
- ELK and Kubernetes base-server generation
- opt-in RAG infrastructure with Qdrant, Elasticsearch, and Ollama, connected to
  generated application/worker consumers through an explicit external named network
- opt-in MinIO S3-compatible local storage
- Identity/Session/Sharded Profile and Scheduled Ingestion input Blueprints

## Docker work

The optional Dockerfile Generator and generated-project daemon build are verified.
Local/integration Compose and Kubernetes base manifests are generated under their
own contracts. Artifact publishing, live deployment, and cloud credentials are not
owned by the Dockerfile Generator.

## Development tooling

Repository navigation and cost-control tooling is maintained through:

- `AGENTS.md`
- `.agents/skills/`
- Serena
- code-review-graph
- Ponytail LITE

Detailed tool procedures belong in Skills, not in `.codex` reference documents.

## Verification policy

Use focused tests first.
Run broader integration or full-suite tests only when the change risk warrants it.
