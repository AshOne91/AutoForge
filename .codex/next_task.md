# Next Task

## Next executable unit: define runtime port-override preflight

OWNERSHIP: AutoForge Kubernetes generator, validated through kis-auto-trading

EVIDENCE: `ProjectSpec` accepts explicit non-overlapping overrides (`49300`,
`49400`, `49600`) and rejects an application/ELK collision at `49400`;
the KIS consumer guide now links the generated `49400` block; the focused
specification tests report `38 passed`.

Define the smallest read-only check that can compare a consumer `.env` port
override with the generated block before Compose starts. Keep it separate from
`ProjectSpec` validation, do not add runtime dynamic allocation, and do not
change deployment topology in that unit.
