# Next Task

## Next executable unit: operator news search query boundary

Add one KIS user-owned, token-protected operator endpoint that calls the existing
`NewsSearchIndexer.search`. Bound `query` and `limit`, return the canonical news
projection, and use the established internal Durable Job token boundary without
modifying generated router output. Verify authentication and ensure internal
`embedding` is absent from the response. Do not create a generic cross-index
router in this unit.

The KIS-local `HybridSearchIndex` now has two concrete consumers, but AutoForge
still must not gain a generic record-to-search generator contract until both
consumer query boundaries are proven and the two projections are deliberately
compared. KIS identity and account records remain excluded because they contain
credential or personal investment-profile data and have no established
search/relevance use case.
