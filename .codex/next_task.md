# Next Task

## Next executable unit: KIS RabbitMQ cluster profile

OWNERSHIP: AutoForge local-environment generator; KIS consumer specification
and scaffolded message handler.

Set the existing KIS local-environment RabbitMQ mode to `cluster`, regenerate
only generated-owned artifacts, and validate one `account.profile.updated`
event through the HAProxy endpoint. Stop one broker, verify relay publish and
worker inbox consumption still recover, then confirm the stopped broker
rejoins. Do not alter generated transport code or the KIS user-owned handler
unless the runtime check demonstrates a concrete defect.
