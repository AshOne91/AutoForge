# Next Task

## Next executable unit: KIS market-data provider boundary

Inspect the existing KIS consumer and the official KIS API contract for one
read-only quotation or market-data slice. Define the user-owned normalized
quote boundary, credential/token ownership, and bounded freshness/cache policy
before implementation. Reuse generated session, logging, Durable Job, and
infrastructure contracts only where the actual read-only slice needs them.

Do not generate order execution, portfolio mutation, trading strategy, or shared
OAuth token coordination until the read-only provider slice demonstrates a
concrete reusable requirement.
