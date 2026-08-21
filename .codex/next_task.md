# Next Task

## Next executable unit: add clustered RAG vector-store generation

Extend the RAG infrastructure generator with an explicit clustered Qdrant
selection while preserving the generated `QDRANT_URL` contract. Generate the
minimum members and stable endpoint required by Qdrant's documented distributed
topology, then prove a member stop does not break a vector-store health request
through that endpoint. Do not change Ollama or consumer domain code in this unit.
