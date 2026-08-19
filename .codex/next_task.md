# Next Task

## Next executable unit: operator durable-job history search projection

Use the generated job-type-scoped history API as KIS's second concrete search
consumer. Its stable source identity is `job_id`; its canonical projection must
exclude payload values and retain only `job_type`, `run_key`, `status`, bounded
error/result summaries, and timestamps. Define one operator query/relevance
requirement, implement this projection in KIS user-owned code, and compare its
fields with the KIS news path. Do not create a generic AutoForge record-to-search
generator contract or move Yahoo-specific normalization into AutoForge in this
unit. KIS identity and account records remain excluded because they contain
credential or personal investment-profile data and have no established
search/relevance use case.

Until that evidence exists, keep KIS search indexing consumer-owned and reuse
the existing selectable RAG infrastructure only.
