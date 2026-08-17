# Next Task

## Next executable unit: verify optional overlay path portability

OWNERSHIP: AutoForge local-environment generator, specification tests, and
environment validation contract

Run the documented Compose commands from the generated project root and from
each overlay directory. Confirm that `LOG_ROOT`, `FILEBEAT_CONFIG`, generated
log mounts, and optional service endpoints resolve to the intended paths without
manual absolute overrides. Correct only a proven path-contract defect; do not
add a new deployment topology.
