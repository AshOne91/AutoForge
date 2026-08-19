# Next Task

## Next executable unit: terminal news-index retry observability

Add one focused consumer test for a final transient `news_index` failure. It
must confirm no fourth Job is created and that the structured log contains the
`news_index_retries_exhausted` event type, original job ID, run key, attempt,
and maximum-attempt fields. Reuse the existing logging path; do not add an
external alert adapter or a new observability service.

Keep terminal signal delivery as the existing observability pipeline concern.
Do not generalize the consumer-owned retry policy into AutoForge without a
second generated consumer needing it.
