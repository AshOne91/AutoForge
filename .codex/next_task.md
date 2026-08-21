# Next Task

## Next executable unit: add a generated local Redis Sentinel profile

Extend the existing local-environment generator so an explicit shared Redis
`sentinel` mode creates the required primary, replica, and Sentinel topology
instead of rejecting it. Preserve the existing generated Sentinel environment
names and application call sites. Add static generation tests and an opt-in
Docker failover drill through one generated consumer contract. Do not replace
the existing Redis Cluster mode or add Redlock, cache policy, or provider-specific
topology.
