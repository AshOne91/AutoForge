# Next Task

## Next executable unit: KIS human-role source and mutation boundary

The named internal service-token slice is complete: Durable Job and operator
search now use different declared credentials. Identify the user-owned
persistent source for human operator roles and one actual state-changing KIS
endpoint. Only then define the smallest authenticated-session role policy and
the request-replay requirement for that mutation.

Do not add a generic role enum, IP allowlist, or replay store solely from the
historical references. Keep read-only market-data work independent, and do not
generate order execution or portfolio mutation before this policy boundary is
proven.
