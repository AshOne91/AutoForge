# Next Task

## Next executable unit: persist the first KIS portfolio snapshot

Add one KIS-owned append-only portfolio snapshot specification in the Account
Shard. A snapshot header belongs to the authenticated user and linked brokerage
connection; its position rows capture the safe fields returned by the existing
read-only holdings client. Generate the SQL/Alembic and repositories before
implementing one authenticated capture path that validates the active
`kis:default` connection before provider I/O and writes the header and positions
in one shard transaction. Verify deterministic fake-provider capture, user/shard
isolation, empty holdings, and rollback on persistence failure. Do not execute
orders, calculate investment advice or risk, store credentials, or add a generic
broker abstraction.
