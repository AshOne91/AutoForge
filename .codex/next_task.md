# Next Task

## Next executable unit: adopt the generated realtime backplane in KIS

Select `tooling.realtime.backplane: redis_pubsub` in both KIS standalone and HA
specifications, regenerate only the expected AutoForge-owned files, and prove
the generated standalone/Cluster configuration is importable. Do not add a
WebSocket route, user-channel policy, notification publisher, or durable-path
change in this unit: adoption first proves the ownership and topology boundary;
live notification delivery is a separate vertical slice.

Do not add email, SMS, webhooks, automatic orders, or default Redis changes in
this unit. Do not run the explicitly opt-in KIS balance integration check.
