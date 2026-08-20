# Next Task

## Next executable unit: select the SMS delivery contract

Select one Korean production SMS provider using its current official API,
pricing, sender-registration, and test-mode documentation. Then add only a
provider-neutral `SmsDelivery` contract plus a deterministic fake and that one
adapter; a paid or credentialed live delivery is not part of the first slice.

Do not create a generic signal transport, change the KIS default Redis
specification, or run the explicitly opt-in KIS balance integration check.
