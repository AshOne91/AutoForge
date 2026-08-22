# Next Task

## Next executable unit: close the first missing local HA proof

The active Roadmap delivery gate permits only reusable service and local logical
HA work. Inspect the existing generated service-composition contract and its
focused tests to identify the first selected service that lacks a verified
single/HA profile or an appropriate restart/failover/rejoin proof. Implement
only that smallest missing proof or generator correction, validate it with the
focused test and local runtime drill when the contract requires Docker, then
record the result in the existing status/roadmap owners. Do not add KIS business
domain behavior.
