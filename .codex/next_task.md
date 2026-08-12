# Next Task

## Next product slice: KIS retry observability

The next executable work is in `kis-auto-trading`, not AutoForge.

OWNERSHIP: user-owned

EVIDENCE: the Yahoo provider enforces a positive timeout and classifies
timeout/provider failures. KIS now schedules up to three durable collection
attempts with 2- and 4-second delays. The durable-job handler remains
scaffolded/preserved, so its business behavior is consumer-owned.

Add one operator-visible record for an exhausted Yahoo collection retry path.
Keep the canonical news record, idempotent persistence, `news_index` handoff,
and existing delayed-retry contract unchanged.

Do not add another provider, a retry framework, RAG reranking, or an AutoForge
generator change in this slice unless the focused consumer work exposes a shared
contract defect.

The next AutoForge change is justified only if this consumer-owned work reveals
a reusable generated-environment or specification defect.
