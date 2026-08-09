# Next Task

## KIS consumer vertical-slice validation

The generated-project Docker build context, PostgreSQL DDL reproducibility, and
Redis/session generation reproducibility are verified. Global and Shard
SQLAlchemy/Alembic routing and message/outbox generation are now explicitly
covered. The next bounded contract is to validate the generated stack in the
`kis-auto-trading` consumer.

### Scope

- inspect the existing KIS validation path
- validate one generated vertical slice without patching generated-owned files
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
