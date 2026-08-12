---
name: model-routing
description: Choose the lowest-cost Codex model and reasoning level sufficient for a bounded AutoForge development task. Use when deciding whether to keep, downgrade, or upgrade the current model, especially before nontrivial implementation, debugging, architecture, distributed-systems, security, financial, or production-critical work.
---

# Model Routing

## Goal

Model routing is a cost-control procedure, not a quality ranking.

Choose the cheapest model and lowest reasoning level that can complete the
current bounded task safely, correctly, and verifiably.

Never trade away:

- correctness
- compatibility
- security
- data integrity
- public contracts
- test coverage
- transaction safety
- production safety

Prefer evidence, focused tests, and narrow context before increasing model cost.

## Default route

For normal AutoForge development, start from:

GPT-5.6 Luna / Medium

For mechanical work:

GPT-5.6 Luna / Light

Default escalation path:

Luna
→ Terra
→ Sol

GPT-5.4 Mini, GPT-5.4, and GPT-5.5 are not default routing choices.
Use them only for a concrete compatibility or capability reason.

The burden of proof is on escalation.

## Current vs recommended setting

Always distinguish:

- CURRENT SETTING: what the user has actually selected.
- RECOMMENDED SETTING: the cheapest setting sufficient for the next bounded task.

The agent cannot silently switch settings.

Report:

- KEEP
- DOWNGRADE
- UPGRADE

## Complexity rule

Classify the requested change, not the surrounding technology.

Complex technology does not automatically imply an expensive route.

Examples:

- editing an Outbox test is not automatically Extra High
- renaming an async function is not automatically High
- modifying EventBus boilerplate is not automatically Terra
- changing a shard-related test is not automatically Extra High
- changing several files is not automatically High

If a change follows an existing pattern, has bounded scope, and can be verified
with focused tests, prefer Luna even when the subsystem is sophisticated.

Do not escalate merely because the task mentions:

- async
- EventBus
- PluginManager
- Registry
- Pipeline
- Redis
- RabbitMQ
- PostgreSQL
- Docker
- Outbox
- Inbox
- sharding
- transactions
- distributed systems

## Model guidance

### GPT-5.6 Luna

Default model.

Use for:

- source exploration
- code explanation
- documentation
- tests
- boilerplate
- ordinary implementation
- CRUD
- API changes
- existing-pattern features
- localized bugs
- normal multi-file changes
- ordinary async code
- moderate refactors
- focused debugging

Try Luna first unless a concrete risk justifies Terra.

### GPT-5.6 Terra

Use when meaningfully stronger reasoning is required.

Examples:

- complex business logic
- state machines
- difficult multi-module debugging
- transaction-boundary changes
- messaging semantics
- consistency-sensitive changes
- retry/recovery design
- ordering guarantees
- significant API/DB design
- difficult async interactions
- partial architecture changes

Do not choose Terra merely because the repository is large or several files
must change.

### GPT-5.6 Sol

Sol is exceptional, not a daily driver.

Sol is prohibited unless at least one hard-gate condition is satisfied:

1. Terra has already failed on the same bounded problem.
2. A demonstrated race condition or difficult concurrency failure exists.
3. The task changes distributed consistency guarantees.
4. The task changes transaction boundaries with material data-integrity risk.
5. The task changes ordering/delivery guarantees across distributed components.
6. The task is security-critical with material risk from a wrong conclusion.
7. The task is financial-critical with material risk from a wrong conclusion.
8. A production-critical cross-system failure has an unclear cause.
9. A major architecture decision spans multiple interacting subsystems and a
   concrete limitation of Terra has been identified.

These are NOT sufficient reasons for Sol:

- many files
- large repository
- unfamiliar code
- async code
- database code
- EventBus
- Redis
- RabbitMQ
- Outbox
- Inbox
- sharding
- important code
- desire for extra confidence
- desire for a second opinion

If no hard-gate condition exists:

DO NOT RECOMMEND SOL.

## Reasoning levels

### Light

Use for:

- locating symbols/files
- explanations
- renames
- imports
- typos
- docs
- configuration
- repetitive changes
- obvious localized fixes

### Medium

Default for normal development:

- features
- tests
- CRUD
- APIs
- existing-pattern implementation
- limited refactors
- ordinary backend logic
- well-understood bugs

### High

Use when deeper interaction reasoning is needed:

- uncertain failures
- multi-module call flow
- async execution tracing
- state transitions
- nontrivial refactors
- meaningful design tradeoffs

### Extra High

Reserve for:

- architecture changes
- race conditions
- concurrency
- transaction consistency
- distributed consistency
- message ordering
- idempotency semantics
- sharding design
- Outbox/Inbox guarantees
- cross-service failures

### Ultra

Exceptional only.

Recommend Ultra only if:

- Extra High has already proved insufficient, or
- an incorrect conclusion has unusually severe irreversible risk.

Before recommending Ultra, explicitly explain why Extra High is insufficient.

## Reasoning ceiling

Default ceilings:

TRIVIAL   → Light
LOW       → Light or Medium
MEDIUM    → Medium
HIGH      → High
VERY HIGH → Extra High
EXTREME   → Extra High

Ultra requires separate explicit justification.

Do not use High or above merely to increase confidence.

## One-dimension escalation

Increase only one dimension at a time.

Bad:

Luna / Medium
→ Sol / Extra High

Good:

Luna / Medium
→ Luna / High

or:

Luna / Medium
→ Terra / Medium

If reasoning depth is insufficient:
increase reasoning first while keeping the model.

If model comprehension/capability is insufficient:
increase the model while keeping reasoning.

Increase both only when evidence shows both are inadequate.

## Failure policy

Do not escalate after one failure.

First failure:

- inspect the exact error
- narrow the failing path
- inspect relevant symbols
- retry a focused correction

Second failure:

increase ONE dimension only:

- reasoning, or
- model

Third failure:

rerun model routing.

Immediate escalation is justified only when new evidence reveals a materially
higher-risk category.

## Model switching and cache efficiency

Avoid frequent model switching inside one coherent bounded task.

Prefer:

one task
→ one model
→ meaningful task boundary
→ optional model change

Bad:

Luna
→ Terra
→ Luna
→ Sol
→ Luna

inside one small debugging loop.

Good:

Terra for a difficult design decision
→ task boundary
→ Luna for implementation
→ task boundary
→ Luna/Light for mechanical cleanup

Prefer changing reasoning before changing models when deeper reasoning is the
only issue.

Do not keep an expensive model merely to preserve cache.

If the next substantial phase clearly needs less capability, downgrade at that
task boundary.

## Context budget

Routing itself must be cheap.

Before routing:

- inspect at most 1-3 likely relevant symbols or small file sections
- do not scan the whole repository
- do not read every `.codex` document
- do not run the full test suite
- use Serena symbol/reference lookup when narrower
- do not inspect the repository at all if the user request already gives enough
  information to classify the task

Preferred exploration order:

exact error/request
→ symbol
→ references
→ relevant symbol bodies
→ targeted file sections
→ broader search only if necessary

## Verification over model cost

Prefer:

cheaper model
+ small change
+ focused test
+ verification

over:

expensive model
+ speculative large change

Passing focused tests are not a reason to repeat the work using Sol solely for
confidence.

## Required routing report

Before a new substantial bounded development task, output:

[MODEL ROUTING]

TASK:
<one sentence>

DIFFICULTY:
TRIVIAL / LOW / MEDIUM / HIGH / VERY HIGH / EXTREME

CURRENT SETTING:
<model / reasoning if known>

RECOMMENDED MODEL:
<model>

RECOMMENDED REASONING:
Light / Medium / High / Extra High / Ultra

CURRENT SETTING SUFFICIENT:
YES / NO

SETTING CHANGE:
KEEP / DOWNGRADE / UPGRADE

COST:
VERY LOW / LOW / MEDIUM / HIGH / VERY HIGH

RATIONALE:
- <concrete reason>

EXPECTED SCOPE:
- relevant files/modules:
- expected changed files:
- required tests:

CHEAPER ALTERNATIVE:
<only if useful>

CHEAPER ALTERNATIVE RISK:
<only real technical risk>

ESCALATION CONDITION:
<concrete evidence>

RECOMMENDED SETTING:
<MODEL> / <REASONING>

## Approval behavior

If SETTING CHANGE is DOWNGRADE or UPGRADE:

- stop before source exploration, tests, edits, external actions, or further
  implementation planning;
- wait for a subsequent user message that confirms or changes the setting and
  explicitly authorizes progress.

If SETTING CHANGE is KEEP, continue when the existing user request authorizes
implementation. Do not require a duplicate approval.

If the current setting is unknown, do not report KEEP. Ask the user to confirm
the current setting before continuing.

Do not silently change the user's selected model or reasoning level.

## High-cost warning

When recommending:

- Sol
- Extra High
- Ultra

also output:

[COST WARNING]

Concrete reason higher capability is required:
<reason>

Cheaper alternative:
<alternative>

Why the cheaper alternative is materially insufficient:
<reason>

If these cannot be answered concretely, do not recommend the expensive setting.

## Final principle

Optimize for:

required quality
+
minimum sufficient model
+
minimum sufficient reasoning
+
minimum sufficient context
+
focused verification

Do not optimize for maximum model capability.
