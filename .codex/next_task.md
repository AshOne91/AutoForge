# Next Task

## Next executable unit: verify durable news collection through OpenSearch

OWNERSHIP: AutoForge Kubernetes generator, validated through kis-auto-trading

EVIDENCE: The generated OpenSearch RAG profile responds on `49460`; a probe
document survived an OpenSearch container restart and was then removed. With
`embeddinggemma`, the KIS search client indexed and retrieved a live news probe
using keyword plus vector search.

Run the generated durable news-collection path against the same OpenSearch and
Ollama services, preserving its retry and outbox contracts. Keep model
distribution, collector security, multi-host storage, and production
backup/restore outside this unit.
