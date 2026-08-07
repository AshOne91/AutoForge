# Model Routing Guidance

## Purpose

Model routing is a cost-control procedure, not a ranking of model quality. Choose
the cheapest model and reasoning level that can still complete the bounded task
safely and correctly. Correctness, compatibility, security, and test coverage must
not be traded away to reduce cost.

The agent must distinguish two facts:

- **Current setting**: the model and reasoning level already selected for this
  session, such as `GPT-5.6 Sol / Light`.
- **Recommended setting**: the least expensive setting judged sufficient for the
  next bounded task.

The agent cannot silently switch the current setting. It only reports whether the
user should `UPGRADE`, `DOWNGRADE`, or `KEEP` it.

## Routing order

Prefer models in this order when each is available and sufficient:

1. GPT-5.4 Mini
2. GPT-5.6 Luna
3. GPT-5.6 Terra
4. GPT-5.6 Sol

GPT-5.4 and GPT-5.5 are not default choices when their price/performance tier
overlaps Terra or Sol. Use them only when a concrete capability or compatibility
reason justifies them.

Increase one dimension at a time. For example, try a higher reasoning level on the
same model or the next model at the same reasoning level; do not jump directly
from Mini/Medium to Sol/Extra High without evidence.

## Reasoning levels

- **Light**: locating files, reading or explaining code, renames, imports, typos,
  simple configuration or documentation edits, repetitive boilerplate, and clear
  localized bug fixes.
- **Medium**: ordinary feature work, CRUD, API additions, tests, limited refactors,
  and implementations that follow an existing pattern.
- **High**: multi-file interactions, async flows, state transitions, uncertain test
  failures, and meaningful trade-off analysis.
- **Extra High**: architecture changes, race conditions, transaction or cache
  consistency, distributed systems, message ordering, idempotency, sharding,
  Outbox/Inbox, and cross-service failures.
- **Ultra**: exceptional cases where Extra High has already proved insufficient or
  the cost of a wrong conclusion is unusually severe. State the concrete reason
  Extra High is insufficient before recommending Ultra.

## Model guidance

- **GPT-5.4 Mini**: default for searches, code reading, documentation, tests,
  boilerplate, small refactors, and clear bounded features.
- **GPT-5.6 Luna**: ordinary multi-file backend work, async code, medium debugging,
  or cases where Mini has a concrete risk of error.
- **GPT-5.6 Terra**: complex business logic, state machines, transactions,
  messaging, consistency, significant API/DB design, and partial architecture work.
- **GPT-5.6 Sol**: exceptional architecture decisions, difficult distributed or
  concurrency failures, data-integrity risk, and security-, financial-, or
  production-critical work. Do not select Sol merely because it is available.

After a difficult decision is complete, route later implementation, tests, and
documentation independently. A task that began on Sol does not require Sol for
every remaining step.

## Required report before work

For a new task, inspect only enough relevant context to classify it, then report:

```text
[MODEL ROUTING]

TASK: <one-sentence summary>
DIFFICULTY: TRIVIAL / LOW / MEDIUM / HIGH / VERY HIGH / EXTREME
RECOMMENDED MODEL: <model>
RECOMMENDED REASONING: Light / Medium / High / Extra High / Ultra
CURRENT SETTING SUFFICIENT: YES / NO
SETTING CHANGE: UPGRADE / DOWNGRADE / KEEP
COST: VERY LOW / LOW / MEDIUM / HIGH / VERY HIGH

RATIONALE:
- <reason>

EXPECTED SCOPE:
- relevant files or modules
- expected number of changed files
- required tests

ALTERNATIVE AND RISK: <only when applicable>
ESCALATION CONDITION: <concrete evidence that requires escalation>

RECOMMENDED SETTING: <MODEL> / <REASONING>
```

If changing the setting is required for correctness, stop after this report and
wait for the user to change it and explicitly say to proceed. A cost-saving
`DOWNGRADE` is advisory: when the current setting is sufficient and the user has
already explicitly said to proceed, start the bounded work without asking for
duplicate approval.

## Failure and escalation

Do not escalate after one failure. First narrow the failing path and inspect the
error using the current setting. On a second failure, increase only one of the
model or reasoning dimensions. Rerun routing after a third failure or when evidence
shows the problem is materially more complex than initially classified.

Before increasing model cost, narrow the scope, search for the relevant symbol,
class, function, or error message, avoid unrelated files and generated artifacts,
make a small change, and verify it with focused tests. Passing tests are not a
reason to rerun the whole review with a larger model unless a material risk remains.
