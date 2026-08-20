# Next Task

## Next executable unit: verify message-worker restart recovery in the isolated profile

Extend the existing isolated single-host verifier after its healthy
three-application-replica realtime proof: restart the generated message worker,
wait for its health check, then repeat the same local notification smoke once.
This proves recovery of the existing RabbitMQ consumer and Redis backplane path
without changing its delivery or persistence guarantees.

Keep the stack disposable and do not add acknowledgement, replay, rate-limit,
or external-delivery policy.
