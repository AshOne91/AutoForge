# Next Task

## Next executable unit: fix the first KIS order-intent and risk boundary

Before generating an order module, compare the current KIS account/portfolio
contracts with the relevant Base Server and game-server lineage and record one
ADR for a non-executing `OrderIntent` lifecycle. The decision must assign
user/account-shard ownership, require request idempotency, place a fail-closed
`RiskDecision` before every provider call, separate intent from provider
execution/conciliation, and define secret-free audit events. Reject any design
that treats an API request or queue delivery as proof of execution. Do not add a
live KIS order call, investment strategy, recommendation, or speculative generic
broker abstraction in this unit.
