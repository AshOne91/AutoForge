# Next Task

## Next executable unit: mark a caller-owned in-app notification as read

In KIS, add one authenticated user endpoint that loads an `InAppNotification`
from the caller's account shard, rejects a record owned by another user with
`404`, and persists only `read_at` through the generated `find_by_id` and
`save` contract. Map unavailable shard/database failures to a detail-safe
`503`. Do not add cross-user, operator, bulk-read, or delivery-provider
behavior.

Do not add email, SMS, WebSocket, webhook, automatic order, provider selection,
or default Redis changes in this unit. Do not run the explicitly opt-in KIS
balance integration check.
