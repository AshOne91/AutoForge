# Next Task

## Dockerfile Generator completed

The minimal optional Dockerfile Generator is implemented and verified.

### Scope

- optional Docker configuration in ProjectSpec
- deterministic Dockerfile rendering
- GenerationPlan integration
- generated ownership and content hashes
- built-in generator/plugin registration
- focused regression tests

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

1. keep the bounded Docker generator contract stable
2. use Serena for exact symbol/reference navigation
3. use CRG only if structural impact analysis is needed
4. keep Ponytail LITE active
5. run focused Docker/spec/plugin tests first
6. expand testing only when justified

Do not perform unrelated refactoring.
