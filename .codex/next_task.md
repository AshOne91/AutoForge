# Next Task

## Next product slice: KIS news-provider resiliency

The next executable work is in `kis-auto-trading`, not AutoForge.

OWNERSHIP: user-owned

EVIDENCE: the Yahoo provider, canonical PostgreSQL persistence, durable
`news_index` handoff, and selectable-search indexing are implemented and
runtime-verified. The durable-job handler remains scaffolded/preserved, so its
business behavior is consumer-owned.

Implement one bounded provider failure contract for the current Yahoo Finance
adapter: timeout, error classification, and retry-safe behavior. Keep the
canonical news record and durable-job contract unchanged.

Do not add another provider, a retry framework, RAG reranking, or an AutoForge
generator change in this slice.

The next AutoForge change is justified only if this consumer-owned work reveals
a reusable generated-environment or specification defect.
