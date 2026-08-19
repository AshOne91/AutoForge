# Next Task

## Next executable unit: KIS operator-only human endpoint

The named internal service-token slice is complete, the user-owned profile `PUT`
suppresses sequential duplicate Outbox events, and AutoForge now generates a
fail-closed `EndpointSpec.access_level` guard over Redis `current_session`.
KIS has its first local `user` to `operator` provisioning CLI, including an
audit record and session revocation. It still needs one non-destructive,
operator-only human endpoint to prove the complete authenticated request flow.

The global identity store is the persistence boundary because login reads it
before creating the Redis session. The reusable Identity Blueprint generates the
account-level and audit persistence contract, and KIS uses an incremental
migration for its existing database. The next endpoint must reuse the generated
operator guard rather than create an independent role check. Keep it read-only,
do not expose account-level mutation, and do not add a generic IP allowlist or
request replay store solely from the historical references.

Keep read-only market-data work independent, and do not generate order execution
or portfolio mutation before this policy boundary is proven.
