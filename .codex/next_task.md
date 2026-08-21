# Next Task

## Next executable unit: prove read-only cache corruption falls through safely

Add focused fake-transport tests proving that malformed or stale Redis cache
payloads for a domestic price or holdings list are ignored and the existing
read-only KIS request is used instead. Keep cache TTLs and KIS request/response
semantics consumer-owned. Do not make a live KIS request or introduce order,
portfolio-policy, or generated stale-data behavior. Fix AutoForge only if this
consumer proof reveals a generated-contract defect.
