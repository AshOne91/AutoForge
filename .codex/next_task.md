# Next Task

## Next executable unit: durable-job cancellation integration validation

The next executable work is in AutoForge.

OWNERSHIP: AutoForge architecture and generation contract

EVIDENCE: AutoForge now generates a token-protected cancellation endpoint.
`requested` Jobs transition to `cancelled`; duplicate cancellation is
idempotent; `running` or terminal Jobs return a conflict; an already delivered
message cannot invoke a cancelled Job's handler because worker claim is atomic.

Run the same contract against the local PostgreSQL, RabbitMQ relay, and
durable-job worker. Verify that cancellation commits before relay claim, status
remains `cancelled`, and no handler-side canonical record is written. Do not
reset unrelated local data or imply that cancellation reverses a completed
external side effect.

Do not add a new scheduler, provider, retry framework, RAG reranking, or
external alert channel in this slice.
