# Next Task

## Next executable unit: add replicated RAG inference generation

Extend the RAG infrastructure generator with an explicit replicated Ollama
selection while preserving the generated `OLLAMA_BASE_URL` contract. Each member
must own its model data; do not share a writable model volume or download a model
implicitly. Generate the stable endpoint and prove one healthy inference member
continues serving the lightweight readiness path after another member stops. Do not
change vector/search collection ownership or consumer domain code in this unit.
