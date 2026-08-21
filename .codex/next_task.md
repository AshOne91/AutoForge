# Next Task

## Next executable unit: verify replicated Ollama member rejoin

Extend the existing opt-in replicated Ollama Docker drill after stopping one
member and proving stable proxy readiness. Start the stopped member, wait until all
three Ollama services are healthy, and confirm the unchanged `/api/tags` proxy
endpoint still responds. Do not download a model, share member volumes, or claim
inference failover; model preparation remains an explicit operator step.
