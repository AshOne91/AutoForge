# Next Task

## Next executable unit: expose in-app notifications through a user-scoped read endpoint

In KIS, add one authenticated user endpoint that reads the generated bounded
`InAppNotificationRepository.list_by_user_id` contract from the caller's
account shard. Return only the caller's newest 100 records. Map unavailable
shard/database failures to a detail-safe `503`; do not expose cross-user,
operator, mark-as-read, or delivery-provider behavior.

Do not add email, SMS, WebSocket, webhook, automatic order, provider selection,
or default Redis changes in this unit. Do not run the explicitly opt-in KIS
balance integration check.
