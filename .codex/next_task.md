# Next Task

## Next executable unit: verify worker recovery after broker restart

The next executable work spans AutoForge and kis-auto-trading.

OWNERSHIP: AutoForge generation contract, validated through kis-auto-trading

EVIDENCE: the generated worker now verifies a real RabbitMQ connection through
Compose healthcheck. KIS generation, static Compose validation, focused tests,
and isolated live startup all pass with the worker reaching `healthy`.

Run the smallest isolated KIS Compose check that restarts RabbitMQ and confirms
the worker returns to `healthy` under its generated restart policy. Do not
change current API, Outbox, or Durable Job ownership, and do not leave test
containers or volumes running.

Do not introduce a generic service framework, broker cluster, or unrelated
deployment abstraction in this slice.
