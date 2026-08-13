# Next Task

## Next executable unit: codify PostgreSQL HA failover verification

OWNERSHIP: AutoForge generation contract, validated through kis-auto-trading

EVIDENCE: AutoForge generates an optional local three-node Patroni PostgreSQL
cluster with a three-member etcd DCS and HAProxy at the existing `postgres:5432`
writer endpoint. KIS generation, static Compose validation, focused tests, live
startup, logical database initialization, leader promotion, and node recovery
passed.

Turn the demonstrated procedure into one isolated KIS runtime verification:
confirm one leader and two streaming replicas, stop the active leader, wait for
HAProxy to reach the promoted writer, restore the stopped node, and confirm it
rejoins as a replica.

Do not add read routing, a production database deployment framework, backup
automation, or an unrelated service abstraction in this slice.
