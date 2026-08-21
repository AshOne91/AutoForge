# Next Task

## Next executable unit: verify generated idempotency route through Redis Sentinel failover

Add one opt-in generated FastAPI integration drill for an endpoint that already
selects `EndpointSpec.idempotency`. Complete its first request before a Sentinel
primary change, then use a fresh generated application/provider connection to
replay that completed response after the elected master is stable. Reuse the
existing request-replay and Sentinel contracts; do not add consumer-domain
policy, retries for uncertain in-flight work, or a new durability guarantee.
