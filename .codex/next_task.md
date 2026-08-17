# Next Task

## Next executable unit: KIS news ingestion through RabbitMQ cluster

OWNERSHIP: KIS user-owned news handler using AutoForge-generated Durable Job,
Outbox, RabbitMQ, and search infrastructure contracts.

Submit one bounded existing `news_collection` Durable Job through the public
API against the verified RabbitMQ cluster. Verify its generated `news_index`
handoff reaches a terminal status and only then inspect the existing search
backend result. Do not change the news provider, handler, or search adapter
unless the vertical runtime path proves a concrete defect.
