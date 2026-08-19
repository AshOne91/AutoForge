# Next Task

## Next executable unit: news-index retry boundary

Inspect the KIS `news_index` Durable Job when its selected RAG backend or
embedding provider is unavailable. Decide whether the existing consumer-owned
bounded retry pattern can safely be reused with `source_keys`, stable run keys,
and explicit transient-error classification. Prove the current failure path
first; do not add a generic AutoForge retry policy, a new queue, or a scheduler
unless more than one generated consumer needs that contract.

Keep backend-specific HTTP handling in KIS unless the evidence identifies a
generated runtime contract as the responsible boundary.
