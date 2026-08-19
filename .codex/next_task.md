# Next Task

## Next executable unit: align the legacy KIS scale-out Redis contract

The current generated Compose profile and operator endpoint live flow are
verified. The remaining bounded issue is the legacy `compose.integration.yaml`
profile: it supplies `REDIS_CLUSTER_URL`, while the current session provider
starts from `REDIS_URL`. Reconcile that environment contract against the
provider's actual standalone/cluster client behavior, then rerun only the
legacy scale-out health and session checks. Do not change the Identity or
operator authorization contract as part of this task.
