# Next Task

## Next product decision: KIS retry alert destination

The next executable work is in `kis-auto-trading`, not AutoForge.

OWNERSHIP: user-owned

EVIDENCE: the Yahoo provider enforces a positive timeout and classifies
timeout/provider failures. KIS schedules up to three durable collection attempts
with 2- and 4-second delays and logs an error when the final attempt fails. The
durable-job handler remains scaffolded/preserved, so its business behavior is
consumer-owned.

Choose the external destination for that existing error signal (for example,
structured log shipping or a notification adapter). Keep the canonical news
record, idempotent persistence, `news_index` handoff, and delayed-retry contract
unchanged.

Do not add another provider, a retry framework, RAG reranking, or an AutoForge
generator change in this slice unless the focused consumer work exposes a shared
contract defect.

The next AutoForge change is justified only if this consumer-owned work reveals
a reusable generated-environment or specification defect.
