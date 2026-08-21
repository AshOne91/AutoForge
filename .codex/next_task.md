# Next Task

## Next executable unit: persist the first KIS account connection

Add one KIS-owned `BrokerageAccountConnection` specification placed in the
Account Shard by `user_id`. Store only non-secret metadata and the fixed
`kis:default` credential reference from ADR-0005. Regenerate before adding one
authenticated, idempotent link path and one authenticated read path that use the
existing session/shard dependencies. Verify generated persistence, isolation
from other users, secret-value exclusion, and a disposable PostgreSQL round
trip. Do not persist holdings, accept credentials in an API request, or add a
generic multi-broker abstraction.
