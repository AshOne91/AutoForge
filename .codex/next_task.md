# Next Task

## Next executable unit: identify a second concrete search consumer

Before adding a generic AutoForge record-to-search generator contract, establish
a second concrete consumer with a stable source identity, canonical document
projection, and query/relevance requirement. The inspected `base_server` RAG
service is reference material, not that evidence: it accepts free-form documents
and falls back to a content hash when an identifier is absent. Identify an actual
project-owned producer, then compare it with the KIS news path to find genuinely
shared fields and the ownership boundary. Do not create a one-consumer abstraction
or move Yahoo-specific normalization into AutoForge. KIS identity and account
records are excluded: they are credential or personal investment-profile data and
have no established search/relevance use case.

Until that evidence exists, keep KIS search indexing consumer-owned and reuse
the existing selectable RAG infrastructure only.
