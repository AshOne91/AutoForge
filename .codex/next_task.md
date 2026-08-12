# Next Task

## Next product decision: KIS terminal retry alert policy

The next executable work is in `kis-auto-trading`, not AutoForge.

OWNERSHIP: user-owned

EVIDENCE: the Yahoo provider enforces a positive timeout and classifies
timeout/provider failures. KIS schedules up to three durable collection attempts
with 2- and 4-second delays, logs a final failure, and its generated Filebeat
profile has runtime-verified delivery to Elasticsearch. The durable-job handler
remains scaffolded/preserved, so its business behavior is consumer-owned.

Choose whether the existing structured log signal should create an operator alert,
and, if so, where it should go. Keep the canonical news record, idempotent
persistence, `news_index` handoff, delayed-retry contract, and generated log
collection unchanged.

Do not add another provider, a retry framework, RAG reranking, or an AutoForge
generator change in this slice unless the focused consumer work exposes a shared
contract defect.

The next AutoForge change is justified only if this consumer-owned work reveals
a reusable generated-environment or specification defect.
