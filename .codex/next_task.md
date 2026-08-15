# Next Task

## Next executable unit: define the single-host Docker startup contract

OWNERSHIP: AutoForge Kubernetes generator, validated through kis-auto-trading

EVIDENCE: `tooling.local_environment.host_port_base: 49400` now drives both the
generated integration services and the optional single-host public proxy. Focused
generator tests and KIS generation validation pass.

Specify the smallest platform-neutral contract for Docker restart policy,
durable volumes, health checks, and operator startup after host reboot. Keep
OS-specific service managers, AWS UserData, Kubernetes bootstrapping, and
production backup/restore outside this unit.
