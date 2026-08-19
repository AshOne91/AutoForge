# Next Task

## Next executable unit: operator durable-job history query boundary

Add one KIS user-owned, token-protected operator endpoint that calls the existing
`DurableJobHistorySearchIndexer.search`. Bound `query` and `limit`, return only
the safe projection, and use the established internal Durable Job token boundary
without modifying generated router output. Verify an authenticated query through
the disposable HA Nginx route and preserve the no-`payload`/no-`embedding`
response contract.

The KIS-local `HybridSearchIndex` now has two concrete consumers, but AutoForge
still must not gain a generic record-to-search generator contract until this API
boundary is proven and the two projections are deliberately compared. KIS identity
and account records remain excluded because they contain credential or personal
investment-profile data and have no established search/relevance use case.
