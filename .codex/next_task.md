# Next Task

## Next executable unit: single-host proxy profile contract

Generate the same KIS specification into a disposable workspace with its
lightweight default and HA profiles. Confirm the intended profile boundary:
the default profile may stay direct and resource-light, while the HA profile
must generate a reverse proxy and the declared application replica topology.
Run the narrow generator tests that own this contract. If HA generation does
not produce the proxy, trace the AutoForge source before changing consumer
files or adding a second Compose stack.

Preserve the single-server resource-saving profile. Do not make the lightweight
default HA by accident, and do not modify running local Docker projects.
