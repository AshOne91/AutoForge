# Next Task

## Next executable unit: RAG-unavailable durable-worker readiness check

OWNERSHIP: AutoForge local-environment generator and generated worker runtime
contract.

Stop one declared RAG endpoint in the local KIS overlay and verify the
RAG-enabled Durable Worker becomes unready without changing its RabbitMQ
consumer contract. Restore the endpoint and verify the worker returns healthy.
Do not couple the separately managed Compose projects or alter RAG-free
profiles.
