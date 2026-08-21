# Next Task

## Next executable unit: verify generated Memcached client recovery after process restart

Extend the existing opt-in generated Memcached runtime drill. Exercise the
generated key-value adapter, terminate the Memcached process so Compose's current
restart policy restores it, then prove a fresh key can be set and read through
the unchanged adapter contract. Treat pre-restart cache loss as valid cache-miss
semantics; do not claim data replication, durable recovery, or Memcached HA.
