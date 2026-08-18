# Next Task

## Next executable unit: RAG endpoint bootstrap preflight

OWNERSHIP: AutoForge local-environment generator and generated worker runtime
contract.

Review whether the generated bootstrap should perform a bounded read-only
endpoint check for the selected RAG search backend and Ollama after the external
network check but before application startup. Keep the existing Worker
healthcheck as the final readiness authority; do not merge Compose projects or
make RAG mandatory for RAG-free profiles.
