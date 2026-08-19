# Next Task

## Next executable unit: select an operator log-query contract

Before an application route reads terminal-retry logs, select a supported
observability provider and define its secret, retention, redaction, and bounded
operator response contract. The current local Filebeat/Elasticsearch profile is
development-only collection and is not sufficient. Do not route logs through
the RAG hybrid-search abstraction or add a generic cross-index router.

KIS identity and account records remain excluded because they contain credential
or personal investment-profile data and have no established search/relevance use
case.
