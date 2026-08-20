# ADR-0004: Keep durable notifications separate from live realtime hints

## Status

Accepted as the boundary for the first KIS in-app notification use case.
No Redis Pub/Sub backplane is implemented by this decision.

## Context

AutoForge currently generates `tooling.realtime` as an in-process
`RealtimeHub`. It can fan out a message to subscribers connected to one
application process, but it has no route, identity policy, persistence, broker
fan-out, replay, or cross-replica guarantee.

KIS already has a stronger path for user notifications: a global Signal delivery
intent is delivered through the transactional Outbox/Inbox path, then stored as
an account-shard `InAppNotification`. The authenticated notification read API is
the recovery path for disconnected clients and failed live delivery.

Redis Pub/Sub is suitable only for a live hint in this design. Redis documents
its Pub/Sub delivery as at-most-once: a subscriber that cannot process a message
loses it permanently. RabbitMQ remains the durable routing layer; exchanges
route published messages to bound queues or streams.

## Decision

1. `InAppNotification` persistence is the user-visible source of truth.
   RabbitMQ Outbox/Inbox remains the durable path that creates it.
2. A future live-notification implementation may publish a minimal hint only
   after the account-shard transaction commits. It must never publish before the
   durable record exists.
3. The first backplane topology is one environment-scoped notification channel.
   Every application replica subscribes once; each replica forwards a received
   hint only to its own locally connected, authenticated user channel. The hint
   carries only the notification identifier and recipient identifier needed for
   local routing. It contains no session token or mutable notification payload.
4. A disconnected client, a Pub/Sub outage, a process restart, or a missed hint
   is recovered by `GET /api/notifications`. Duplicate hints are permitted; a
   client uses the notification identifier to de-duplicate its display.
5. The backplane reuses the selected Redis runtime topology and secret contract.
   AutoForge does not generate a second Redis deployment, and its local cluster
   drill does not claim protection from physical-host failure.
6. The generic `RealtimeHub` remains local fan-out only. A future generated
   backplane must make its opt-in selection, subscription lifecycle,
   reconnection/health behavior, and topology compatibility explicit rather than
   silently changing the existing `RealtimeSpec` contract.

## Consequences

The durable record is never lost merely because a WebSocket process or Redis
subscriber is unavailable. Redis Pub/Sub has no acknowledgement, replay, or
durable retry responsibility in this design. RabbitMQ is not used as a direct
WebSocket transport, so application replicas do not need per-replica durable
queue topology for an ephemeral hint.

This does not yet define a generated WebSocket endpoint, user authentication,
authorization, message schema, retry policy, channel partitioning, delivery
metrics, or a Redis client implementation. Those remain separate, consumer-led
implementation work after the opt-in backplane contract exists.

## References

- [Redis Pub/Sub delivery semantics](https://redis.io/docs/latest/develop/pubsub/)
- [RabbitMQ exchanges and queue routing](https://www.rabbitmq.com/docs/next/exchanges)
