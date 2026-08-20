# Next Task

## Next executable unit: verify the Outbox relay path in the isolated profile

Extend the existing isolated single-host verifier with one test-only event that
is first written through the existing Transactional Outbox in the automation
store. Require the running generated outbox relay to publish it, the recovered
message worker to persist the notification, and Nginx to deliver its hint. Then
restart the relay and repeat the same proof once.

Keep the stack disposable and do not add acknowledgement, replay, rate-limit,
or external-delivery policy.
