# Next Task

## Next executable unit: live durable-job history search verification

In a disposable KIS workspace generated from `autoforge.ha.yaml`, preserve the
committed KIS user-owned code and start the resource-gated RAG overlay. Create or
reuse a `news_collection` Durable Job, request `durable_job_history_index` through
the generated internal token API, and verify that `operator-durable-jobs-v1`
receives its safe projection. Run one keyword-plus-vector operator query such as
`news collection`; confirm that the returned document has no `payload` field or
payload values. Do not print API tokens or document values that are not part of
the safe projection. Do not mutate the normal single-host Compose profile to make
this drill work.

The KIS-local `HybridSearchIndex` now has two concrete consumers, but AutoForge
still must not gain a generic record-to-search generator contract until this live
slice is verified and the two projections are deliberately compared. KIS identity
and account records remain excluded because they contain credential or personal
investment-profile data and have no established search/relevance use case.
