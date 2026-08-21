# Next Task

## Next executable unit: verify distributed MinIO writes with one member stopped

Locate the existing opt-in distributed MinIO Docker drill and reuse its generated
four-member topology and stable proxy endpoint. After stopping one member, write
a new object through the unchanged endpoint and read that same object back before
restoring the member. Preserve the current object-storage contract; do not add a
provider abstraction, retry policy, or physical-host HA claim.
