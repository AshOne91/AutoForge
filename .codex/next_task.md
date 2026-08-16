# Next Task

## Next executable unit: document generated port blocks in the consumer guide

OWNERSHIP: AutoForge Kubernetes generator, validated through kis-auto-trading

EVIDENCE: `ProjectSpec` accepts explicit non-overlapping overrides (`49300`,
`49400`, `49600`) and rejects an application/ELK collision at `49400`;
AutoForge reports `486 passed, 6 skipped`, and the KIS specification regenerates
successfully with its `49400`, `49500`, and `49600` allocations.

The next smallest documentation-only unit is to make the consumer guide point
to the generated port-block contract. Do not add runtime dynamic allocation or
change deployment topology in that unit.
