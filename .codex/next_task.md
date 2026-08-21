# Next Task

## Next executable unit: verify the generated Redis session store through Sentinel failover

The generated session-store adapter already accepts Redis Sentinel runtime
settings, and the local Sentinel profile has a verified primary/replica/quorum
topology. Add one opt-in Docker drill that reads a session before and after the
primary changes using the same generated store client. Preserve session data and
expiry semantics; do not add consumer authentication or user-domain policy.
