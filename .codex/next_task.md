# Next Task

## Next executable unit: run a local Compose realtime-notification smoke drill

With non-production runtime values explicitly supplied, start the existing KIS
single-host Compose profile and prove one authenticated notification WebSocket
receives one minimal hint after an account-shard notification transaction.
Record only a focused local result; do not call the KIS API, add an external
delivery provider, or weaken the existing fail-closed environment validation.

This drill requires a deliberate local Docker action and runtime configuration,
so it must not begin silently.
