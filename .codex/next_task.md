# Next Task

## Next executable unit: restore profile-event consumer after RabbitMQ recovery

The next executable work is in kis-auto-trading.

OWNERSHIP: kis-auto-trading user-owned integration runtime

EVIDENCE: the KIS full scale-out verifier reaches Outbox `published` after a
RabbitMQ restart, but `kis.profile.events` has zero consumers and its event is
not inserted into the Inbox. The durable-job queue still has its worker,
isolating the defect to profile-event consumer lifecycle rather than broker or
Outbox publication.

Trace the user-owned profile-event worker service and its Compose lifecycle.
After a broker restart it must reconnect, redeclare the queue, consume the
published event once, and write one Inbox record. Preserve the AutoForge
generated environment and Durable Job worker contracts.

Do not add a broker cluster, retry framework, or external alert channel in this
slice.
