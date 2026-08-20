# Next Task

## Next executable unit: generate an opt-in Redis realtime backplane boundary

Implement the smallest AutoForge contract implied by ADR-0004. Preserve the
default in-process `RealtimeHub`; an explicit opt-in must generate a Redis
Pub/Sub adapter with lifecycle, bounded reconnection, and a deterministic fake.
It must reuse an already-selected Redis topology rather than create a second
Redis service. Verify the specification, generation plan, and generated
contract only; KIS WebSocket routing, user-channel policy, notification
publisher, and KIS adoption are separate later units.

Do not add email, SMS, webhooks, automatic orders, or default Redis changes in
this unit. Do not run the explicitly opt-in KIS balance integration check.
