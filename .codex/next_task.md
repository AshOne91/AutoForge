# Next Task

## Next executable unit: provider-selected observability query adapter

When a production observability provider is selected, define a deployment-owned
query adapter with its secret, retention, redaction, and bounded operator
response contract. The current local Filebeat/Elasticsearch profile remains
development-only collection; generated applications do not query logs directly.
Do not route logs through the RAG hybrid-search abstraction or add a generic
cross-index router.

KIS identity and account records remain excluded because they contain credential
or personal investment-profile data and have no established search/relevance use
case.
