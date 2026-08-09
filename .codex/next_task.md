# Next Task

## Generated deployment baseline

The generated-project Docker build context, PostgreSQL DDL reproducibility, and
Redis/session generation reproducibility are verified. Global and Shard
SQLAlchemy/Alembic routing and message/outbox generation are now explicitly
covered. The `kis-auto-trading` consumer vertical slice now passes all focused
and full tests. The next bounded contract is a deployment baseline generated
from the existing Docker build contract.

### Scope

- inspect the existing Docker build contract and deployment generators
- choose one local deployment artifact with no cloud or Kubernetes behavior

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
