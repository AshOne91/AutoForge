---
name: autoforge-vertical-slice
description: Use when implementing an AutoForge or consumer feature that should reuse existing specifications, generators, plugins, infrastructure, and runtime contracts while being delivered as a verified end-to-end vertical slice.
---

# AutoForge Vertical Slice

## Principle

Build the smallest meaningful path through the requested feature first. Reuse existing capabilities before adding code, and add dependencies only when the slice reaches them. A passing end-to-end slice is the checkpoint for expanding the feature.

AutoForge is the source project. Consumer projects such as `kis-auto-trading` validate generated output. Use `autoforge-ownership` for the permanent repair location when generated and user-owned code meet.

## Required workflow

### 1. Establish the existing path before editing

Inspect only the requested path, then identify:

- the current entry point and direct callers;
- matching specifications, generators, plugins, services, and helpers;
- manifest ownership and generated/scaffolded/user-owned boundaries;
- the smallest existing runtime path that can carry the feature.

Prefer Serena symbol/reference lookup, then targeted text search. Do not create a new abstraction until the reuse check has a concrete answer.

### 2. Define one vertical slice

Write the slice mentally as:

```text
trigger/input → existing orchestration → new behavior → observable output
```

The slice must have one useful outcome, one bounded data contract, and one focused verification command. Do not build unrelated infrastructure first.

For a large feature, keep the main flow real and narrow, then expand its dependent capabilities one at a time. Each expansion must leave the previous slice working.

### 3. Respect the generation boundary

For specification, database, module, application, Docker, or infrastructure work, use this order:

```text
specification → generator/plugin plan → generated artifacts → user-owned extension
```

For database work specifically:

```text
ModuleSpec.database
→ generated SQLAlchemy model/repository
→ generated raw SQL/Alembic migration
→ generated Docker/runtime migration path
→ application-specific repository or handler
```

Never hand-write a generated model, generated migration, or generated SQL file before proving that the existing generator cannot express the requirement. Validate the specification and inspect the generation plan before adding consumer code.

### 4. Reuse decision gate

Before introducing a class, function, file, or dependency, answer in order:

1. Can an existing symbol or service do this?
2. Can an existing specification or generator produce it?
3. Can an existing plugin be configured for it?
4. Is the missing behavior domain-specific and therefore user-owned?
5. Is the generator contract genuinely insufficient and worth improving?

If the answer is 1–3, reuse it. If the answer is 4, keep the extension in the consumer project. Choose 5 only with a focused AutoForge test and regenerated consumer evidence.

### 5. Verify each increment

After every bounded increment:

1. run the focused test or generation validation;
2. inspect generated diff and ownership changes;
3. run the affected consumer test;
4. run broader tests only when shared contracts or generation output warrant it.

Do not continue layering new dependencies on a failing slice. Classify the failure as product, test, collection, ownership, or environment failure first.

### 6. Stop conditions

Pause before editing and report when:

- ownership is unknown or generated output conflicts with preserved user code;
- a requested DB or infrastructure artifact has not been checked against its existing specification/generator;
- the next step changes transaction, delivery, idempotency, or sharding guarantees beyond the current bounded slice;
- the feature requires a new architectural source of truth or model routing escalation.

## Completion report

Report briefly:

- the completed slice and reused capabilities;
- changed generated versus user-owned files;
- focused and affected verification results;
- the smallest next slice and any deferred generator capability.
