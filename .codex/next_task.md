# Next Task

## Next executable unit: add clustered RAG search generation

Extend the RAG infrastructure generator with an explicit clustered search
selection while preserving the generated `RAG_SEARCH_URL` contract. Start with
one search backend and prove a member stop does not break a keyword-health
request through the stable endpoint. Do not change Qdrant, Ollama, or consumer
domain code in this unit.
