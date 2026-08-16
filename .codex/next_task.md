# Next Task

## Next executable unit: verify generated file-log persistence after restart

OWNERSHIP: AutoForge Kubernetes generator, validated through kis-auto-trading

EVIDENCE: The Task Scheduler task is registered, the bootstrap script waits for
Docker, starts the generated 49400 port block, and `GET /health` returned HTTP
200 both before and after a real Windows reboot.

Confirm a generated application log remains available under `logs/` after one
application restart and one host reboot. Keep centralized log shipping,
multi-host storage, Linux/AWS bootstrap, and backup/restore outside this unit.
