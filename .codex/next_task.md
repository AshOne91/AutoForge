# Next Task

## Next executable unit: read holdings through the linked KIS account

Add one authenticated, read-only KIS consumer path that loads the current
user's generated `BrokerageAccountConnection` from the Account Shard before any
provider I/O. Accept only the active fixed `kis:default` reference, then reuse
the existing lifespan-owned KIS account client and coordinated Redis token.
Verify safe holding projection and prove that another user, a missing or
inactive connection, and an unknown reference all fail before KIS is called.
Use only the deterministic fake provider; do not persist holdings, execute an
order, or add a generic broker/resolver abstraction.
