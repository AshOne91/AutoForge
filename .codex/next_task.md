# Next Task

## Next executable unit: read one persisted KIS portfolio snapshot

Add one authenticated `GET /api/portfolio/snapshots/{snapshot_id}` path that
uses the generated Account Shard repositories. Return the stored header and its
ordered safe position rows only when `snapshot.user_id` matches the current
session user. Verify the correct shard target, missing and foreign snapshot
denial, empty positions, and that the path never accesses the KIS client. Reuse
the existing portfolio response model; do not add listing/pagination, provider
I/O, order behavior, risk calculation, or a new abstraction.
