# Next Task

## Next executable unit: verify application recovery after dependency restart

The next executable work spans AutoForge and kis-auto-trading.

OWNERSHIP: AutoForge generation contract, validated through kis-auto-trading

EVIDENCE: the generated worker and outbox relay verify real RabbitMQ
connections through Compose healthchecks. KIS generation, static Compose
validation, focused tests, isolated live startup, and a RabbitMQ restart all
pass with both services healthy/reconnected.

Run the smallest isolated KIS Compose check that restarts PostgreSQL and
confirms the generated application returns healthy under its existing restart
policy. Do not change current API, Outbox, or Durable Job ownership, and do not
leave test containers or volumes running.

Do not introduce a generic service framework, broker cluster, or unrelated
deployment abstraction in this slice.
