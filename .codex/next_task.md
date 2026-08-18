# Next Task

## Next executable unit: ingestion/indexing generation-boundary decision

Compare the runtime-verified KIS news flow with the existing AutoForge module
and RAG contracts. Identify the smallest reusable ingestion/indexing contract,
if one exists, without moving domain-specific Yahoo collection, article
normalization, or search mapping into generated code. Confirm generated,
scaffolded, and user-owned boundaries before proposing any specification or
generator change.

Do not create a new contract merely because KIS has a working news extension.
The result must either reuse an existing AutoForge contract or state the exact
consumer requirement that the current contract cannot express.
