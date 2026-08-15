# Next Task

## Next executable unit: restore forwarded headers in the Kubernetes Nginx generator

OWNERSHIP: AutoForge Kubernetes generator, validated through kis-auto-trading

EVIDENCE: The Kubernetes specification exposes independent `proxy_replicas` and
`application_replicas` values, and a focused generator test now proves non-default
values render independently. The single-host Compose specification exposes
`application_replicas` and intentionally keeps one Nginx owner for its single
public host port. The generated Kubernetes template also forwards `X-Real-IP`
but omits `X-Forwarded-For` and `X-Forwarded-Proto`.

Update the AutoForge Kubernetes generator and its focused test, regenerate the
KIS Kubernetes manifest, and verify the generated ConfigMap contains all three
proxy identity/protocol headers. Do not add OAuth token coordination,
SIGTERM/preStop orchestration, or multi-node log storage in this unit.
