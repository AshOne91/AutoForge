# Next Task

## Next executable unit: select a host bootstrap provider for Docker auto-start

OWNERSHIP: AutoForge Kubernetes generator, validated through kis-auto-trading

EVIDENCE: The platform-neutral startup contract now defines `restart:
unless-stopped`, Docker daemon boot, and repeatable `docker compose ... up -d
--wait`. Generated integration and single-host profiles use the explicit 49400
port block.

Choose one target provider (Windows Task Scheduler, Linux systemd, or AWS
UserData) and add only its adapter and verification. Keep other providers,
Kubernetes bootstrapping, and production backup/restore outside this unit.
