# Next Task

## Next executable unit: validate the generated Kubernetes HA profile on a cluster

OWNERSHIP: AutoForge Kubernetes generator, validated through kis-auto-trading

EVIDENCE: The Kubernetes specification exposes independent `proxy_replicas` and
`application_replicas` values, the generator test proves non-default values
render independently, and the generated Nginx template now forwards
`X-Real-IP`, `X-Forwarded-For`, and `X-Forwarded-Proto`. The KIS manifest has
been regenerated with the current 2-proxy/3-application values.

When a disposable Kubernetes context is available, apply the generated manifest
with non-production Secret values and verify both Deployments become ready,
LoadBalancer-to-Nginx-to-ClusterIP routing works, and one proxy/application Pod
can roll without losing readiness. Keep cluster credentials, managed databases,
OAuth token coordination, and multi-node log storage outside this unit.
