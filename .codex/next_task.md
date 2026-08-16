# Next Task

## Next executable unit: validate port override preservation

OWNERSHIP: AutoForge Kubernetes generator, validated through kis-auto-trading

EVIDENCE: `ProjectSpec` now rejects overlapping generated host-port offsets;
AutoForge reports `486 passed, 6 skipped`, and the KIS specification regenerates
successfully with its `49400`, `49500`, and `49600` allocations.

Verify that explicit environment overrides remain valid within their declared
blocks and do not bypass specification-level collision checks. Keep dynamic
port allocation and deployment topology outside this unit.
