# Next Task

## Next executable unit: verify outbox relay recovery after broker restart

The next executable work spans AutoForge and kis-auto-trading.

OWNERSHIP: AutoForge generation contract, validated through kis-auto-trading

EVIDENCE: the generated worker now verifies a real RabbitMQ connection through
Compose healthcheck. KIS generation, static Compose validation, focused tests,
isolated live startup, and a RabbitMQ restart all pass with the worker remaining
`healthy`.

Run the smallest isolated KIS Compose check that restarts RabbitMQ and confirms
the generated outbox relay reconnects or recovers without changing current API,
Outbox, or Durable Job ownership. Do not leave test containers or volumes
running.

Do not introduce a generic service framework, broker cluster, or unrelated
deployment abstraction in this slice.
