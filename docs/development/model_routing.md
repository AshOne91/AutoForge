# Model Routing & Cost Control Guidance

> This is a human-readable guide. The authoritative policy is
> [`.agents/skills/model-routing/SKILL.md`](../../.agents/skills/model-routing/SKILL.md).
> If this guide and the Skill differ, follow the Skill.

## 0. Purpose

Model routing is a strict cost-control procedure.

The objective is NOT to select the strongest available model.

The objective is:

> Choose the cheapest model and lowest reasoning level that can complete the
> current bounded task safely, correctly, and verifiably.

Cost must be minimized aggressively, but the following must never be sacrificed:

- correctness
- compatibility
- security
- data integrity
- transaction safety
- API contracts
- backward compatibility
- test coverage
- error handling
- idempotency
- production safety

Use tests, narrow scopes, and incremental verification to preserve quality before
increasing model cost.

A more expensive model must be justified by concrete technical evidence.

"More powerful", "safer", "better", "important", or "complex-looking" are NOT
sufficient reasons by themselves.


# 1. CURRENT SETTING VS RECOMMENDED SETTING

Always distinguish between:

## Current setting

The model and reasoning level already selected by the user for this session.

Example:

GPT-5.6 Luna / Medium


## Recommended setting

The least expensive model and reasoning level judged sufficient for the NEXT
bounded task.

The agent cannot silently change its own model or reasoning setting.

It may only report:

- KEEP
- DOWNGRADE
- UPGRADE

The user changes the actual setting.


# 2. DEFAULT ROUTE

Unless concrete evidence justifies otherwise, start routing from:

GPT-5.6 Luna / Medium

For purely mechanical work, prefer:

GPT-5.6 Luna / Light


IMPORTANT:

The burden of proof is on escalation.

The agent does NOT need to justify staying on a cheap model.

The agent MUST justify moving to a more expensive model or reasoning level.


# 3. AVAILABLE MODELS

Available models:

- GPT-5.4 Mini
- GPT-5.6 Luna
- GPT-5.6 Terra
- GPT-5.6 Sol
- GPT-5.4
- GPT-5.5


Default cost-oriented routing order:

GPT-5.6 Luna
    ↓
GPT-5.6 Terra
    ↓
GPT-5.6 Sol


GPT-5.4 Mini, GPT-5.4, and GPT-5.5 are NOT default routing choices.

Use them only when there is a concrete capability,
compatibility, regression-testing, or implementation reason to prefer them.

Do not select them merely because they are available.


# 4. AVAILABLE REASONING LEVELS

Available reasoning levels:

- Light
- Medium
- High
- Extra High
- Ultra


Default:

Medium

Use Light whenever the task is sufficiently mechanical.


# 5. CRITICAL COMPLEXITY RULE

The presence of a complex technology does NOT automatically make the requested
task complex.

Classify the complexity of the SPECIFIC CHANGE, not the complexity of the
surrounding system.


Examples:

Editing an Outbox test
!=
designing an Outbox consistency guarantee


Changing an async function name
!=
debugging a race condition


Adding a field to a sharded model
!=
redesigning shard routing


Updating EventBus tests
!=
redesigning event delivery semantics


Adding Redis error handling
!=
designing distributed cache consistency


The following technologies or words MUST NOT automatically trigger expensive
routing:

- async
- EventBus
- Outbox
- Inbox
- Redis
- RabbitMQ
- PostgreSQL
- transaction
- sharding
- Docker
- queue
- worker
- distributed
- messaging
- API
- database


If the requested change:

- follows an existing implementation pattern,
- has a bounded scope,
- and can be verified with focused tests,

prefer Luna even if the subsystem itself is sophisticated.


# 6. MODEL GUIDANCE

## GPT-5.4 Mini

This is not a default routing choice. Use it only when the authoritative Skill's
compatibility or capability exception applies.


## GPT-5.6 Luna

Luna is the default model for normal AutoForge development.

Good Luna tasks include:

- ordinary multi-file backend changes
- moderate API work
- ordinary async code
- medium-complexity debugging
- moderately coupled modules
- nontrivial tests
- medium refactors
- several related business rules
- adapting an existing architecture pattern
- following code across a few modules
- implementation after a harder architectural decision has already been made

Luna should handle a large portion of normal development before Terra is
considered.


## GPT-5.6 Terra

Use Terra only when the task requires meaningfully stronger reasoning.

Good Terra tasks include:

- complex business logic
- meaningful state machines
- difficult debugging
- transaction-boundary changes
- message processing semantics
- significant API or database design
- consistency-sensitive changes
- complex async interactions
- architecture changes affecting several components
- failure recovery design
- retry semantics
- ordering guarantees
- complex idempotency behavior
- difficult cross-module reasoning

Do NOT select Terra only because:

- the repository is large
- several files must change
- the module is important
- the feature uses Redis/RabbitMQ/PostgreSQL
- the code is unfamiliar


## GPT-5.6 Sol

Sol is an exceptional model, not a daily driver.

Use Sol only when a hard-gate condition is satisfied.

Typical Sol-class tasks include:

- major architecture decisions
- difficult distributed-system failures
- demonstrated race conditions
- severe concurrency bugs
- critical data-integrity problems
- distributed consistency changes
- difficult production failures involving multiple subsystems
- security-critical reasoning
- financial-critical reasoning
- material data-loss risk
- a bounded problem that Terra has already failed to solve


# 7. HARD GATE FOR GPT-5.6 SOL

GPT-5.6 Sol is PROHIBITED unless at least ONE of the following is true:

1. Terra has already failed on the same bounded problem.

2. There is evidence of a real race condition or difficult concurrency failure.

3. The requested change modifies distributed consistency guarantees.

4. The requested change modifies transaction boundaries where incorrect behavior
   could cause data corruption or data loss.

5. The requested change modifies ordering guarantees or delivery semantics across
   distributed components.

6. The task is security-critical and a wrong conclusion can create material risk.

7. The task is financial-critical and a wrong conclusion can create material risk.

8. The task is production-critical and involves multiple interacting subsystems
   with an unclear failure cause.

9. A major architecture decision spans multiple interacting subsystems and a
   concrete reasoning limitation of Terra has been identified.


The following are NOT sufficient reasons for Sol:

- many files
- large repository
- unfamiliar repository
- async code
- database code
- EventBus
- Redis
- RabbitMQ
- Outbox
- Inbox
- sharding
- transactions by themselves
- important code
- desire for extra confidence
- desire for a second opinion
- "this looks complicated"
- "this architecture is sophisticated"


If no hard-gate condition is satisfied:

SOL MUST NOT BE RECOMMENDED.


# 8. REASONING GUIDANCE

## Light

Use for mechanical or highly localized work:

- finding files
- finding symbols
- reading code
- explanations
- renames
- imports
- typos
- documentation
- configuration
- simple transformations
- repetitive boilerplate
- obvious localized bug fixes
- simple tests


## Medium

This is the default for normal development:

- ordinary features
- CRUD
- API additions
- tests
- limited refactors
- existing-pattern implementation
- clear multi-file work
- ordinary validation
- ordinary backend logic
- well-understood bugs


## High

Use when meaningful reasoning across interactions is required:

- several modules interact
- async execution flow must be traced
- state transitions must be followed
- a test failure has an uncertain cause
- a moderate architectural trade-off exists
- a refactor has several interaction points
- a bug requires deeper call-path analysis


## Extra High

Reserve for genuinely difficult reasoning:

- architecture changes
- race conditions
- concurrency
- transaction consistency
- cache consistency
- distributed systems
- message ordering
- idempotency semantics
- sharding design
- Outbox/Inbox guarantees
- cross-service failures
- complicated recovery behavior
- data-integrity-sensitive redesign


## Ultra

Ultra is effectively prohibited for normal development.

Consider Ultra only when:

- Extra High has already proved insufficient, OR
- an incorrect conclusion carries unusually severe irreversible risk.

Examples:

- exceptionally difficult race condition
- severe production data corruption
- extremely difficult distributed failure
- critical security reasoning
- critical financial consistency reasoning
- final validation of a major irreversible architecture decision


Before recommending Ultra, explicitly answer:

WHY IS EXTRA HIGH INSUFFICIENT?

If that cannot be answered concretely:

DO NOT RECOMMEND ULTRA.


# 9. REASONING CEILING

Use the following reasoning ceilings by default:

TRIVIAL
→ Light

LOW
→ Light or Medium

MEDIUM
→ Medium

HIGH
→ High

VERY HIGH
→ Extra High

EXTREME
→ Extra High


Ultra requires separate explicit justification.


Do not use:

High
Extra High
Ultra

merely to increase confidence.

Higher reasoning must address an identified reasoning requirement.


# 10. ONE-DIMENSION ESCALATION RULE

Never increase both model and reasoning simultaneously unless there is clear
evidence that BOTH are insufficient.


BAD:

Mini / Medium
→ Terra / High


BAD:

Luna / Medium
→ Sol / Extra High


GOOD:

Mini / Medium
→ Mini / High


OR:

Mini / Medium
→ Luna / Medium


Determine WHAT is insufficient.


If reasoning depth is insufficient:

keep model
+
increase reasoning one level


Example:

Mini / Medium
→ Mini / High


If model capability, comprehension, or reliability is insufficient:

increase model one level
+
keep reasoning


Example:

Mini / Medium
→ Luna / Medium


Only increase both dimensions after separate evidence shows both are inadequate.


# 11. FAILURE AND ESCALATION POLICY

Do not escalate after one failure.


FIRST FAILURE:

- inspect the exact failure
- narrow the path
- inspect the error
- inspect the relevant symbol
- keep the current model and reasoning if reasonable
- make a focused correction


SECOND FAILURE:

Increase only ONE dimension:

- reasoning one level

OR

- model one level


THIRD FAILURE:

Run model routing again.

Reevaluate whether the task is materially more difficult than originally
classified.


Immediate escalation is allowed only when new evidence reveals a clearly
higher-risk category such as:

- race condition
- data corruption
- transaction consistency failure
- distributed consistency failure
- security-critical behavior
- financial-critical behavior


# 12. DOWNGRADE POLICY

A difficult task does NOT justify keeping an expensive model for the entire
workflow.

Route each phase independently.


Example:

Terra / Extra High
→ architecture or consistency decision

then

Luna / Medium
→ implementation

then

Luna / Medium
→ tests

then

Luna / Light
→ documentation


Another example:

Sol / Extra High
→ diagnose a production race condition

then

Terra / High
→ design the fix

then

Luna / Medium
→ implement bounded changes

then

Mini / Medium
→ add tests


When the difficult portion is complete, recommend a downgrade.


Use:

[COST DOWNGRADE RECOMMENDED]

Completed difficult phase:
<description>

Remaining work:
<description>

Recommended cheaper setting:
<model / reasoning>

RECOMMENDED SETTING: <MODEL> / <REASONING>


Do not keep Sol/Terra active merely because the session started with them.


# 13. ROUTING INSPECTION BUDGET

Model routing itself must be cheap.

Do not burn large amounts of context merely to decide which model to use.


Before issuing a routing report:

- inspect at most 1–3 likely relevant symbols or small file sections
- avoid reading entire large files
- avoid repository-wide analysis
- do not run the full test suite
- do not inspect unrelated modules
- prefer symbol/reference lookup
- prefer Serena MCP when it can retrieve narrower context


If the task can be classified from the user's request alone:

DO NOT inspect the repository merely to generate the routing report.


Routing should cost substantially less than doing the task itself.


# 14. CONTEXT & TOKEN EFFICIENCY

Minimize input context aggressively.

Preferred exploration order:

exact error
→ relevant symbol
→ symbol references
→ relevant symbol bodies
→ targeted file sections
→ broader text search
→ entire file only if necessary
→ repository-wide investigation only as a last resort


Avoid:

- rereading the same files
- rereading already available context
- reading entire files when one symbol is sufficient
- reading unrelated tests
- reading large logs in full
- repository-wide architecture analysis for a localized change
- blindly scanning directories
- loading generated artifacts unnecessarily


Do not inspect by default:

- .git
- .venv
- venv
- node_modules
- __pycache__
- .pytest_cache
- build
- dist
- coverage
- caches
- generated artifacts
- large logs


Access these only when the task specifically requires them.


# 15. SERENA MCP TOKEN-EFFICIENCY RULES

When Serena MCP is available, prefer it for source-code exploration when it can
reduce context usage.

Preferred operations include:

- symbol lookup
- symbol overview
- reference lookup
- targeted symbol-body retrieval


Preferred sequence:

symbol
→ references
→ relevant symbol bodies
→ targeted surrounding code


Do NOT automatically read an entire source file after Serena has already returned
enough information.


Use ordinary text/file search when:

- the target is not represented well as a symbol
- searching configuration
- searching documentation
- searching SQL
- searching migrations
- searching exact error strings
- Serena cannot locate the target


Serena is a context-reduction tool, not a mandatory tool.

Do not make unnecessary MCP calls when the answer is already available in the
current context.


# 16. MCP COST CONTROL

More MCP servers do NOT automatically reduce token usage.

Every MCP server may add:

- tool descriptions
- schemas
- instructions
- tool-result context
- latency


Use only MCP servers with a concrete benefit for the current workflow.

Do not add or invoke redundant MCP tools when built-in repository or shell tools
already solve the problem efficiently.


For source navigation:

prefer Serena when useful.

Do not invoke unrelated MCP servers merely because they are available.


# 17. TASK DECOMPOSITION

Prefer several cheap bounded tasks over one massive expensive task.

BAD:

"Analyze the entire repository and redesign the system."


BETTER:

1. locate the failing component
2. identify its callers
3. inspect the relevant contract
4. identify the smallest change
5. implement it
6. add/update focused tests
7. run focused tests
8. expand only if necessary


Large tasks should be decomposed so cheaper models can handle most phases.


Do not route an entire multi-hour task according to its single hardest phase.


# 18. TESTS AS A COST-SAVING QUALITY MECHANISM

Prefer:

cheap model
+
small change
+
strong test
+
verification

over:

expensive model
+
large speculative change


Use tests to reduce uncertainty before increasing model cost.


Preferred development loop:

1. understand the bounded requirement
2. inspect existing tests/patterns
3. make a small change
4. run focused tests
5. inspect failure
6. fix
7. rerun focused tests
8. run broader regression tests only when warranted


Passing focused tests are NOT a reason to rerun the same work using Sol merely for
extra confidence.


Escalate only when a material unresolved risk remains.


# 19. TEST SCOPE CONTROL

Do not automatically run the entire test suite after every small modification.

Prefer:

affected unit test
→ affected module tests
→ integration tests if relevant
→ full suite when the change warrants it


The full suite is appropriate when:

- shared infrastructure changed
- public interfaces changed
- architecture changed
- multiple modules are affected
- release-level validation is requested
- regression risk is substantial


Avoid repeatedly executing expensive tests when focused tests are sufficient.


# 20. MODEL ROUTING REPORT

For every NEW bounded development task, route before implementation.

Inspect only enough context to classify the task.

Then report exactly:


[MODEL ROUTING]

TASK:
<one-sentence description>

DIFFICULTY:
TRIVIAL / LOW / MEDIUM / HIGH / VERY HIGH / EXTREME

CURRENT SETTING:
<current model / current reasoning if known>

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
- <technical reason>
- <technical reason if needed>

EXPECTED SCOPE:
- relevant files/modules:
- expected changed files:
- required tests:

CHEAPER ALTERNATIVE:
<only when applicable>

CHEAPER ALTERNATIVE RISK:
<only real technical risks>

ESCALATION CONDITION:
<concrete evidence that would justify higher cost>

RECOMMENDED SETTING:
<MODEL> / <REASONING>


# 21. WHEN TO STOP AFTER ROUTING

If UPGRADE is required for correctness:

STOP after the routing report.

Wait for the user to change the model/reasoning and explicitly say:

- proceed
- continue
- start
- 진행
- 계속


If DOWNGRADE is recommended only to save cost:

The downgrade is advisory.

If the CURRENT setting is already sufficient and the user has already explicitly
authorized the task, do NOT ask for duplicate approval.

Proceed with the bounded work.


If KEEP:

Proceed when the user's existing request already authorized implementation.


# 22. SOL / HIGH-COST WARNING

Whenever recommending:

- GPT-5.6 Sol

OR

- Extra High

OR

- Ultra

include:


[COST WARNING]

This setting may consume significantly more AI credits.

Concrete reason higher capability is required:
<reason>

Cheaper alternative:
<alternative>

Why the cheaper alternative is materially risky or insufficient:
<reason>


If those fields cannot be answered concretely:

DO NOT recommend the expensive setting.


# 23. NO SPECULATIVE COST NUMBERS

Do not invent estimated credit consumption.

Unless actual usage data or reliable billing data is available, do NOT say:

"This will consume about 20 credits."

"This task should cost about $3."

Instead use relative cost:

- VERY LOW
- LOW
- MEDIUM
- HIGH
- VERY HIGH


Actual credit consumption must be measured from real usage.


# 24. EXAMPLES

## Example A

Task:

"Rename an EventBus event and update its tests."

Recommended:

GPT-5.6 Luna / Light or Medium


Reason:

The surrounding subsystem is architecturally important, but the bounded change is
mechanical and testable.


## Example B

Task:

"Add another plugin using the same existing Plugin interface."

Recommended:

GPT-5.6 Luna / Medium


Reason:

Existing implementation pattern can be followed and verified with tests.


## Example C

Task:

"Fix several related async handlers with a known failing test."

Recommended:

GPT-5.6 Luna / Medium or High


Reason:

Requires multi-file reasoning but does not automatically require Terra.


## Example D

Task:

"Refactor PluginManager and Registry interactions across several modules."

Recommended:

GPT-5.6 Luna / High

Escalate to Terra only if deeper architectural behavior or difficult invariants
are uncovered.


## Example E

Task:

"Add a retry counter to the existing Outbox implementation."

Recommended:

GPT-5.6 Luna / Medium


NOT:

Terra / Extra High merely because the word "Outbox" appears.


## Example F

Task:

"Change Outbox transaction boundaries and guarantee atomic persistence with domain
state."

Recommended:

GPT-5.6 Terra / High or Extra High


Reason:

The requested change modifies transaction and consistency guarantees.


## Example G

Task:

"Investigate actual duplicate financial processing caused by an intermittent race
condition across multiple workers."

Recommended:

GPT-5.6 Terra / Extra High initially.

Sol becomes eligible only when the Sol hard-gate criteria are satisfied.


## Example H

Task:

"Terra / Extra High has repeatedly failed to determine the cause of a confirmed
cross-service race condition that can corrupt financial state."

Recommended:

GPT-5.6 Sol / Extra High

Ultra only if Extra High remains insufficient and the exceptional-risk rule is
satisfied.


# 25. FINAL ROUTING PRINCIPLE

The agent's job is NOT:

"Find the strongest model for the task."


The agent's job IS:

"Find the cheapest execution path that preserves correctness."


Prefer:

smaller scope
+
cheaper model
+
lower reasoning
+
targeted context
+
focused tests
+
incremental verification


before:

larger model
+
higher reasoning
+
larger context


When uncertain between two settings:

start with the cheaper setting unless doing so creates a concrete material risk.


Expensive settings require evidence.

Cheap settings do not.


# 26. CRITICAL COST CONSTRAINT

AI credit consumption must remain tightly controlled.

Past overuse of expensive model/reasoning combinations is NOT acceptable as a
default operating pattern.

Therefore:

- GPT-5.6 Sol is NOT a default model.
- High is NOT the default reasoning level.
- Extra High is exceptional.
- Ultra is extremely exceptional.
- repository-wide analysis is NOT the default exploration strategy.
- more context is NOT automatically better.
- more reasoning is NOT automatically safer.
- more expensive models are NOT automatically higher quality for bounded tasks.


If Luna plus focused tests can safely complete the task:

USE LUNA.


If Terra is sufficient:

DO NOT USE SOL.


If Medium is sufficient:

DO NOT USE HIGH.


If High is sufficient:

DO NOT USE EXTRA HIGH.


If Extra High is sufficient:

DO NOT USE ULTRA.


The final optimization objective is:

QUALITY REQUIRED
+
MINIMUM NECESSARY MODEL
+
MINIMUM NECESSARY REASONING
+
MINIMUM NECESSARY CONTEXT
=
LOWEST SAFE DEVELOPMENT COST
