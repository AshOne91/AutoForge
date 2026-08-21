# Next Task

## Next executable unit: run the identity/session local-HA runtime smoke

Generate a fresh disposable `identity_session_profile` workspace and start its
integration Compose profile. Verify database creation and migrations, the Redis
Cluster topology, generated application health, and declared host ports, then
tear down only that Compose project and its test volumes. Do not implement
consumer-owned login policy, edit generated-owned output, or reuse preserved
consumer containers and volumes.
