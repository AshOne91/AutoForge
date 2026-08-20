# Next Task

## Next executable unit: apply SignalEvent expiry and delivery-intent schema

Use the generated additive schema-evolution contract in KIS to declare the
producer-owned SignalEvent expiry and global per-subscription delivery intent.
Regenerate the models, raw SQL, and Alembic revision; preserve the immutable
existing `0001_signal` baseline and do not hand-write its replacement.

Do not add the fan-out worker, external channel delivery, automatic order, or
default Redis changes in this unit. Do not run the explicitly opt-in KIS balance
integration check.
