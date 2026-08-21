# Next Task

## Next executable unit: verify generated single-host Nginx process recovery

Reuse the same generated profile-server Compose subset without starting its
RabbitMQ, Airflow, ELK, or RAG services. After Nginx crosses Docker's restart-policy
activation window, terminate its PID 1 from inside the container, verify
`RestartCount` increases and the public `/health` endpoint recovers. A brief gap is
valid for the intentionally singleton local proxy; do not add a second host-port
owner, process manager, or multi-host HA claim.
