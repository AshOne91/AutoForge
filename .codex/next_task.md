# Next Task

## Next executable unit: verify post-reboot bootstrap settings

OWNERSHIP: AutoForge Kubernetes generator, validated through kis-auto-trading

EVIDENCE: the read-only `validate-ports` command is implemented and tested;
the generated Windows bootstrap checks the fully resolved Compose JSON;
an intentional `49999` collision fails before `up`; the live bootstrap reached
healthy replicas with `/health` `200`; and the registered Task Scheduler job
was triggered successfully.

After an operator-approved host or Docker Desktop restart, query the task's
last result and verify the proxy health endpoint and replica recovery. Do not
change runtime allocation or deployment topology in that unit.
