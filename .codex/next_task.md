# Next Task

## Next executable unit: prove two generated application compositions

Add the smallest specification and generation proof that one KIS project can
produce two named FastAPI application compositions from reusable domain modules:
a default combined API composition and one independently deployable selected
composition. Preserve module ownership, Global/Shard placement, and existing
transport contracts. Do not move domain policy, introduce cross-service calls,
or couple composition to replica count.

After that proof, resume the consumer-owned SignalEvent delivery intent and
expiry-policy decision before adding fan-out.

Do not change the KIS default Redis specification or run the explicitly opt-in
KIS balance integration check.
