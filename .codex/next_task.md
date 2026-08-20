# Next Task

## Next executable unit: define generated additive schema evolution

The KIS domain policy now selects a durable, per-subscription SignalEvent
delivery intent in the global `automation` store, with producer-owned immutable
expiry and no direct channel delivery. Before implementing that intent, define
the smallest AutoForge additive schema-evolution contract that preserves
scaffolded immutable `0001` baselines and produces a new reproducible revision.

Do not hand-write a generated model, raw SQL, or Alembic revision in KIS before
the existing generator boundary is extended or explicitly shown insufficient.
Do not change the KIS default Redis specification or run the explicitly opt-in
KIS balance integration check.
