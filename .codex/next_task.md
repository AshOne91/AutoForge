# Next Task

## Next executable unit: define SignalEvent delivery intent

Choose and document one consumer-owned delivery target and expiry policy for
`SignalEvent` before adding fan-out. Keep the policy outside AutoForge's generic
subscription transport and do not invoke Realtime, Notification, LLM, or SMS
until the delivery contract and guarantee are explicit.

Do not change the KIS default Redis specification or run the explicitly opt-in
KIS balance integration check.
