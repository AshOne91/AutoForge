# Next Task

## Next executable unit: define the Kibana availability boundary

Inspect the current generated ELK Compose contract and decide whether multiple
Kibana instances can safely share its generated state and configuration without
changing the local operator endpoint or weakening security. If that contract is
not yet bounded, record the reason and choose the next already-documented
service-level HA verification instead. Do not add application log-query APIs or
change consumer domain code in this unit.
