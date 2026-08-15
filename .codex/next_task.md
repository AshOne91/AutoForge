# Next Task

## Next executable unit: validate explicit local port blocks across generated profiles

OWNERSHIP: AutoForge Kubernetes generator, validated through kis-auto-trading

EVIDENCE: `docs/architecture/local_port_policy.md` defines 100-port blocks and
the KIS blueprint now declares `tooling.local_environment.host_port_base: 49400`.
Generated local services therefore use 49400/49410/49430/49431/49440, while
container-internal ports remain unchanged.

Confirm the generated Compose config and KIS scale-out documentation enumerate
all host bindings without collisions. Keep Kubernetes Service ports, cluster
credentials, OAuth token coordination, and multi-node log storage outside this
unit.
