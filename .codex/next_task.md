# Next Task

## Next executable unit: establish the FastAPI WebSocket transport adapter

Extend the existing opt-in RealtimeHub only with a generic FastAPI WebSocket
adapter that turns one connected socket into a `RealtimeSubscriber`. Keep the
route path, authentication, authorization, channel subscription policy,
message serialization, persistence, broker fan-out, and workflow triggers
consumer-owned.

Do not change the KIS default Redis specification, treat a Realtime boundary as
an EventBus replacement, create a default application route, or run the
explicitly opt-in KIS balance integration check automatically.
