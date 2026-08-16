# Next Task

## Next executable unit: verify bootstrap recovery after Windows re-login

OWNERSHIP: AutoForge Kubernetes generator, validated through kis-auto-trading

EVIDENCE: The Task Scheduler task is registered, the bootstrap script waits for
Docker, starts the generated 49400 port block, and `GET /health` returned HTTP
200 through Nginx after a manual task run.

Log out and back in (or reboot once), wait for Docker Desktop and the two-minute
task delay, then verify `docker ps` and `http://127.0.0.1:49400/health`. Do not
change Linux, AWS, Kubernetes, or backup/restore behavior in this unit.
