# Next Task

## Next executable unit: verify the OpenSearch hybrid news query path

OWNERSHIP: AutoForge Kubernetes generator, validated through kis-auto-trading

EVIDENCE: The generated OpenSearch RAG profile responds on `49460`; a probe
document survived an OpenSearch container restart and was then removed. The KIS
OpenSearch search client focused tests pass.

Run one end-to-end news indexing and hybrid keyword/vector query with an
explicitly available Ollama embedding model. Keep model distribution, collector
security, multi-host storage, and production backup/restore outside this unit.
