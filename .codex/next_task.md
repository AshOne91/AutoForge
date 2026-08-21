# Next Task

## Next executable unit: verify distributed MinIO member rejoin after a degraded write

Extend the existing opt-in distributed MinIO Docker drill after the one-member
outage write. Restart the stopped member, wait for the generated cluster health,
then read the outage-written object through the stable endpoint and confirm all
four members are available. Reuse the current topology; do not add repair
automation, a provider abstraction, or a physical-host HA claim.
