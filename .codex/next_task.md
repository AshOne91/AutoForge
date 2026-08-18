# Next Task

## Next executable unit: HA RAG bootstrap runtime drill

OWNERSHIP: AutoForge generated Windows bootstrap and KIS HA-profile validation.

In a disposable HA-profile runtime, start the generated RAG overlay with its
inference profile, run the generated Windows bootstrap, and prove the new
in-network endpoint preflight passes before Compose startup. Then stop one RAG
dependency long enough to prove bootstrap fails with the explicit preflight
error, restore it, and return the consumer repository to the lightweight default
profile. Keep the durable-worker healthcheck as the final readiness authority;
do not merge Compose projects or make RAG mandatory for RAG-free profiles.
