# Next Task

## Next executable unit: external news-provider resilience boundary

Inspect the existing KIS Yahoo provider path and its durable `news_collection`
consumer. Establish the smallest reusable resilience boundary for an external
provider: explicit timeout, classified transient failure, and bounded retry
ownership. Reuse existing AutoForge and KIS infrastructure where it already
exists; do not add a queue, scheduler, or generic provider framework until the
current call path demonstrates that it needs one.

Keep Yahoo-specific normalization in the consumer project. Fix AutoForge only
if the evidence shows that a generated runtime contract is responsible.
