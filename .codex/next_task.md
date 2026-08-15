# Next Task

## Next executable unit: verify the Windows bootstrap adapter on the host

OWNERSHIP: AutoForge Kubernetes generator, validated through kis-auto-trading

EVIDENCE: `tooling.single_host.bootstrap_provider:
windows_task_scheduler` now generates
`deploy/single-host/windows/start-compose.ps1`. The script uses the explicit
49400 port block and repeatable `docker compose ... up -d --wait` command.

Run a PowerShell syntax check and, on the operator host, register a Task
Scheduler task that starts after Docker Desktop. Verify one reboot/restart drill
without changing Linux, AWS, Kubernetes, or backup/restore behavior.
