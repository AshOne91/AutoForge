# Next Task

## Next executable unit: verify RabbitMQ restart recovery in the isolated profile

Extend the existing isolated single-host verifier after its Redis recovery proof:
restart RabbitMQ, wait for the generated Outbox relay and message worker health,
then repeat one Transactional Outbox notification smoke. This checks their
existing broker reconnection path without claiming clustered broker HA.

Keep the stack disposable and do not add acknowledgement, replay, rate-limit,
or external-delivery policy.
