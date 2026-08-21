# Next Task

## Next executable unit: verify generated application recovery after process termination

Locate the smallest existing opt-in generated application Compose drill with a
stable Nginx endpoint. After the application container has crossed Docker's
restart-policy activation window, terminate its PID 1 from inside the container,
verify `RestartCount` increases and health returns, then call `/health` through
the unchanged Nginx endpoint. Reuse the current generated contracts; do not add a
process manager, application retry policy, or multi-host HA claim.
