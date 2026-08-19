# Next Task

## Next executable unit: assess terminal retry log operator boundary

Locate the existing KIS terminal-retry Elasticsearch fields and their current
redaction/configuration boundary. If an existing safe contract exists, add one
bounded user-owned, token-protected read endpoint; otherwise record the concrete
blocker. Do not route this through the RAG hybrid-search abstraction and do not
create a generic cross-index router.

KIS identity and account records remain excluded because they contain credential
or personal investment-profile data and have no established search/relevance use
case.
