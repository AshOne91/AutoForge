# Next Task

## Next executable unit: decide SignalEvent delivery intent and expiry policy

In the KIS consumer, choose and record the first delivery intent for persisted
`SignalEvent` records and its expiry policy before adding any fan-out. Reuse the
existing Outbox, Inbox, Realtime, and notification contracts where applicable;
do not create a generic subscription transport or move KIS domain policy into
AutoForge.

Keep `SignalEvent` records unrouteable until a selected consumer and bounded
delivery contract exist. Do not change the KIS default Redis specification or
run the explicitly opt-in KIS balance integration check.
