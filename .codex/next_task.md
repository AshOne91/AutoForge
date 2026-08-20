# Next Task

## Next executable unit: bound persisted portfolio ownership

Analyze the current KIS account model, generated Global/Shard database contract,
and reference lineage to determine whether a persisted portfolio projection is
needed after the live read-only holdings boundary. Record one smallest safe
follow-up slice and its storage ownership; preserve the existing read-only
operator route while doing so.

Do not add a portfolio table, cache, polling/Durable Job, order action, or live
KIS request during this analysis. Do not infer that an external brokerage account
identifier belongs in a user shard without evidence from current contracts.
