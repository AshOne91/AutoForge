# Next Task

## Next executable unit: audit optional local service recovery contracts

OWNERSHIP: AutoForge local-environment generator, specification tests, and
environment validation contract

Inspect only the already-generated optional local service profiles: RAG search
(Elasticsearch/OpenSearch), object storage (MinIO), and observability (ELK).
For each enabled service, determine whether the generated Compose contract has
an explicit restart policy, health check, and persistent-volume or bind-mount
boundary.

Add or correct only a missing single-host recovery guarantee, with focused
specification/generator tests. Preserve the existing provider abstraction and
do not introduce clusters, managed-cloud integrations, or a new deployment
topology in this unit.
