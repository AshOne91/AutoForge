# Rules

Never change architecture without approval.

One PR = One feature.

One commit = One purpose.

Always use type hints.

Always use pytest.

Do not use global variables.

Prefer composition over inheritance.

Dependency Injection first.

## Model routing

Before starting a new implementation task, evaluate the task against the model and
reasoning level that are actually active in the current session. The agent cannot
change that setting itself; it may only recommend `UPGRADE`, `DOWNGRADE`, or `KEEP`.

Present the routing decision first and wait when the user must change the setting.
When the current setting is suitable and the user has already explicitly said to
proceed, continue without asking for duplicate approval.

Use the smallest model and reasoning level that can complete the task safely and
correctly. For the complete reporting format and escalation rules, see
`docs/development/model_routing.md`.
