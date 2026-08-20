# Next Task

## Next executable unit: expose in-app notifications through a user-scoped read path

Determine whether the existing AutoForge repository contract can express a
user-scoped ordered read of generated `InAppNotification` records. If it can,
use that generated contract for one authenticated KIS read endpoint. If it
cannot, add only the smallest general repository operation and its focused
AutoForge test before regenerating KIS. Keep notification records account-shard
local and return only the caller's records.

Do not add email, SMS, WebSocket, webhook, automatic order, provider selection,
or default Redis changes in this unit. Do not run the explicitly opt-in KIS
balance integration check.
