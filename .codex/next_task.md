# Next Task

## Next executable unit: KIS privileged-role provisioning and session revocation

The named internal service-token slice is complete, the user-owned profile `PUT`
suppresses sequential duplicate Outbox events, and AutoForge now generates a
fail-closed `EndpointSpec.access_level` guard over Redis `current_session`.
KIS still needs its first privileged-role provisioning path and an operator-only
endpoint to prove the complete human authorization flow.

The global identity store is the persistence boundary because login reads it
before creating the Redis session. The user-owned provisioning action must set
one account's access level, audit the action, and revoke that user's existing
sessions before the new authority takes effect. It must not create a hardcoded
initial administrator or expose a public self-service role-change API.

Do not add a generic IP allowlist or replay store solely from the historical
references. Keep read-only market-data work independent, and do not generate
order execution or portfolio mutation before this policy boundary is proven.
