# Next Task

## Global/Shard persistence boundary verification

The generated-project Docker build context, PostgreSQL DDL reproducibility, and
Redis/session generation reproducibility are verified. The next bounded
contract is to validate explicit Global versus Shard persistence boundaries.

### Scope

- inspect the existing database specification and SQLAlchemy/Alembic tests
- verify one representative Global and Shard specification end to end
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
