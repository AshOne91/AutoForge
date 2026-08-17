# Next Task

## Next executable unit: RAG-aware durable-worker readiness

OWNERSHIP: AutoForge local-environment generator and generated worker runtime
contract.

Determine whether a generated Durable Job worker that is configured to execute
RAG indexing should report ready while its declared external RAG services are
unreachable. If the existing generator contract says readiness represents all
required runtime dependencies, add the smallest conditional readiness probe and
focused generator test. Do not couple separately managed Compose projects or
make RAG mandatory for projects that did not select it.
