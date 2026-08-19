# Next Task

## Next executable unit: KIS human-role persistence and provisioning boundary

The named internal service-token slice is complete, and the user-owned profile
`PUT` suppresses sequential duplicate Outbox events. KIS still has no persistent
human role field, role assignment workflow, or human operator endpoint.

Before adding `required_roles`, prove the first human operator use case and its
bootstrap/provisioning path. The candidate persistence boundary is the global
identity store because login reads it before creating the Redis session, but it
must not be added as an unused enum or a hardcoded initial administrator.

Do not add a generic role enum, IP allowlist, or replay store solely from the
historical references. Keep read-only market-data work independent, and do not
generate order execution or portfolio mutation before this policy boundary is
proven.
