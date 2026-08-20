# Next Task

## Next executable unit: verify the manual market-price snapshot job request

KIS now has a generated `market_price_snapshot` Durable Job contract and a
user-owned worker handler, but the operator-facing trigger must be proved before
any scheduling is considered. Add one focused KIS test through the existing
generated Durable Job request route: an authorized internal caller requests one
six-digit stock-code snapshot, which creates the durable record and its outbox
message without calling KIS. Reject an invalid payload before any job request.

Do not add a schedule, automatic polling, public endpoint, order behavior, or a
second request API. Reuse the generated route, service-token guard, repository,
and outbox contract; the consumer owns only the market-price payload validation
if the generic request route cannot express it.
