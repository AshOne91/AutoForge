# Next Task

## Next executable unit: establish safe single-host worker replica coverage

The active Roadmap delivery gate permits only reusable service and local logical
HA work. Trace the generated Outbox relay, message worker, and Durable Job
worker claim paths before deciding whether an opt-in Single Host replica
configuration is safe. Reuse existing Inbox, Outbox, and job-claim guarantees;
do not claim exactly-once execution or scale a component whose contract cannot
support concurrent replicas. Implement and verify only the smallest safe
generator extension. Do not add KIS business domain behavior.
