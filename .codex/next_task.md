# Next Task

## Next executable unit: assert notification read state in the local smoke drill

Extend the existing KIS-local realtime smoke command after its durable-record
assertion: use the same ephemeral USER session to mark that exact notification
read and confirm the stored `read_at` state. Reuse the existing notification API;
do not add a new API, change delivery guarantees, or call KIS/external providers.

Keep the command optional and operator-invoked; it must not run on normal
application startup.
