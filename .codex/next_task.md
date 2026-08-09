# Next Task

## Generated-project Docker daemon build verification

The generated-project Docker build context, PostgreSQL DDL reproducibility, and
Redis/session generation reproducibility are verified. Global and Shard
SQLAlchemy/Alembic routing and message/outbox generation are now explicitly
covered. The `kis-auto-trading` consumer vertical slice now passes all focused
and full tests. The Dockerfile already provides the minimal local deployment
baseline by running Uvicorn; a separate Compose/Kubernetes generator is not
justified yet. The next bounded contract is an actual Docker daemon build.

### Scope

- run the generated-project Docker build with an available Docker daemon
- verify the image build context and keep deployment credentials out of output

### Current blocker

The Docker CLI is installed, but Docker Engine is unavailable in the current
environment (`docker_engine` named pipe access is denied). Do not add a
Compose/Kubernetes workaround for this environment; retry the same contract
when a Docker daemon is available.

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
