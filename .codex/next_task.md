# Next Task

## Next executable unit: run the realtime smoke through the isolated three-replica profile

Reuse the existing isolated `verify_generated_single_host.py` environment and
the KIS-local realtime smoke contract to prove that one Nginx-routed client
receives a durable notification hint while all three generated application
replicas are healthy. Keep application code replica-agnostic, use a disposable
non-production stack, and retain its existing cleanup guarantee.

Do not add acknowledgement, replay, rate-limit, or external-delivery policy;
this is only a scale-out validation of the existing best-effort hint contract.
