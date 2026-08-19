# Next Task

## Next executable unit: isolated news-index retry runtime drill

In a disposable KIS workspace and non-overlapping port block, start the normal
application/Durable Job stack plus its RAG overlay. Stop only the selected search
backend or Ollama long enough to force one `news_index` retry, restore it, and
confirm that the retry job succeeds using the original canonical `source_keys`.
Inspect Durable Job status and the indexed document count. Clean up only the
disposable project resources afterward.

Do not change production-like long-running local projects during this drill, and
do not generalize the consumer-owned retry policy into AutoForge without a
second generated consumer needing it.
