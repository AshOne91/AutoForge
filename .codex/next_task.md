# Next Task

## Next executable unit: isolated application crash-recovery acceptance drill

OWNERSHIP: AutoForge generated single-host runtime contract and KIS HA-profile
validation.

Define and run one reproducible failure mechanism that Docker recognizes as an
unexpected application-container exit in a disposable, separately named HA
Compose project. Verify `RestartCount` increases, the stopped replica returns
healthy under the generated restart policy, and Nginx `/health` stays HTTP 200
throughout. Do not use `docker stop` or `docker kill` as evidence of restart
policy behavior: Docker treats those as operator-initiated stops. Preserve the
normal KIS workspace and its retained HA volumes; this is an isolated validation
task, not a reason to alter the generated runtime contract.
