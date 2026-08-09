# Next Task

## Shared Redis/session contract verification

The generated-project Docker build context and representative PostgreSQL DDL
reproducibility are verified. The next bounded contract is to validate the
shared Redis/session generation contract.

### Scope

- inspect the existing Redis/session generator and tests
- verify one representative session specification twice
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
