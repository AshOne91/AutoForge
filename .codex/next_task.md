# Next Task

## Next executable unit: live-verify the durable worker readiness boundary

The next executable work spans AutoForge and kis-auto-trading.

OWNERSHIP: AutoForge generation contract, validated through kis-auto-trading

EVIDENCE: the generated worker now has an explicit Compose process-liveness
healthcheck, while migration and RabbitMQ readiness remain dependency-gated.
KIS generation and static Compose validation pass; live container health remains
unverified.

Run the smallest isolated KIS Compose check that starts only the generated
worker dependencies and verifies the worker reaches `healthy`. Do not change
current API, Outbox, or Durable Job ownership, and do not leave test containers
or volumes running.

Do not introduce a generic service framework, broker cluster, or unrelated
deployment abstraction in this slice.
