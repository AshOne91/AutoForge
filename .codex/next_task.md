# Next Task

## Environment realization before Durable Job runtime validation

The generated-project Docker build context, PostgreSQL DDL reproducibility, and
Redis/session generation reproducibility are verified. Global and Shard
SQLAlchemy/Alembic routing and message/outbox generation are now explicitly
covered. The `kis-auto-trading` consumer vertical slice now passes all focused
and full tests. The generated project also builds successfully with Docker
Engine 29.1.2. The managed Redis Cluster URL contract has been verified against
the running KIS integration cluster. The next bounded contract is the durable
Job lifecycle for the KIS News/RAG workflow; the Airflow DAG scaffold follows
that contract. Environment realization is now governed by
`docs/architecture/environment_validation_contract.md`; Compose/Kubernetes
generation remains deferred until a KIS product declaration selects its scope.

### Completed durable Job foundation

- `DurableJobSpec` validates the selected database store and RabbitMQ outbox.
- generated `DurableJobRecord` enforces `(job_type, run_key)` uniqueness.
- generated repository creates the JobRecord and OutboxEvent in one caller-owned transaction.
- generated migration adds the durable job table after the store outbox migration.
- generated FastAPI router provides idempotent trigger and status endpoints.
- generated Worker dispatch validates the event/job contract and performs
  `requested -> running -> succeeded|failed` compare-and-set transitions.
- generated application handler scaffold is preserved for KIS-owned business work.
- a Durable Job `schedule` generates an Airflow DAG that uses its data-interval
  start as the idempotency key, then triggers and polls the internal Job API.
- Durable Job coordinator storage is limited to an explicitly declared Global DB.

### Remaining scope

- validate a generated DAG in a KIS-owned Airflow environment before treating it
  as an operational deployment contract
- add private service identity (mTLS, OIDC, or IAM) before exposing the internal
  Job API beyond its private network
- keep scheduling, retry, timeout, and dependency ownership in Airflow
- keep News parsing, canonical schema, indexing, and RAG ingestion KIS-owned
- preserve EventBus, RabbitMQ, Redis, and generated-file ownership contracts

### Validation prerequisites observed on 2026-08-09

- The local `base`, `autoforge`, and `kis_trade` Python environments do not
  include `apache-airflow`; Docker Engine is available, but no Airflow image is
  present. No image was downloaded or container created for a scaffold-only
  generator contract.
- KIS `autoforge.yaml` currently declares no `durable_jobs`. Its only Global
  database is `identity`; do not infer that it is the right coordinator store
  for a News/RAG workflow without a KIS product decision.

### Completed consumer validation

- KIS manifest confirms FastAPI, PostgreSQL DDL, SQLAlchemy, SessionStore, and
  Messaging artifacts are generated-owned by AutoForge.
- `C:\Users\ldgo9\miniconda3\envs\autoforge\python.exe -m pytest -p
  no:cacheprovider -q` passes all 14 KIS tests.
- The `kis_trade` environment still lacks pytest. The normal pytest command
  stalls during cache-provider cleanup in this environment; disabling only
  `cacheprovider` avoids that external cleanup issue.
- preserve Generator, GenerationPlan, Manifest, ownership, and validation
  contracts

### Constraints

Do not include:

- artifact publishing
- deployment
- AWS/cloud credentials
- Kubernetes
- Docker Compose
- unrelated infrastructure abstractions

Preserve existing Generator, Manifest, ownership, and validation contracts.

### Workflow

1. inspect the existing database generator and SQL/migration test path
2. add the smallest reproducibility assertion needed
3. use Serena for exact symbol/reference navigation
4. use CRG only if structural impact analysis is needed
5. keep Ponytail LITE active
6. run focused tests first and expand only when justified

Do not perform unrelated refactoring.
