---
name: testing-workflow
description: Run and design AutoForge tests efficiently with the smallest useful verification scope. Use when implementing, debugging, refactoring, adding tests, investigating pytest failures, or deciding whether focused, module, integration, or full-suite validation is required.
---

# AutoForge Testing Workflow

## Goal

Maintain correctness while minimizing unnecessary test execution, context usage,
and agent iterations.

Do not use the full test suite as the default verification step.

Use the smallest test scope that can prove or disprove the current change.

## Verification order

Prefer this sequence:

1. exact failing test
2. directly affected test file
3. affected module or feature tests
4. relevant integration tests
5. full suite only when regression risk justifies it

Do not skip directly to the full suite unless the change is broad enough to
require it.

## Before modifying code

If a test already fails:

- inspect the exact failure first
- identify the relevant symbol or execution path
- do not run unrelated tests
- do not rerun the same failing command without a meaningful change or new evidence

If adding behavior:

- locate existing nearby tests
- follow established test patterns where appropriate
- identify the smallest test that proves the new behavior

## During implementation

Prefer a tight loop:

small change
→ focused test
→ inspect result
→ focused correction
→ rerun focused test

Avoid:

large speculative change
→ full pytest
→ large failure output
→ broad repository investigation

## Focused pytest examples

Single test:

pytest tests/path/test_file.py::test_name -q

Single test file:

pytest tests/path/test_file.py -q

Related directory:

pytest tests/services/generation -q

Use the project's actual test structure rather than inventing paths.

## When to expand test scope

Expand from focused tests when:

- the focused test passes
- the change affects shared behavior
- callers or dependents may be affected
- a public contract changed
- generation output changed
- shared registry/plugin behavior changed
- serialization/specification behavior changed
- integration boundaries changed

Expand only one level at a time when practical.

## When full-suite validation is warranted

Run the full suite when one or more of these are true:

- shared core infrastructure changed
- public APIs or contracts changed broadly
- generator behavior affects many outputs
- Plugin/Registry/EventBus/Pipeline foundations changed
- architecture changed
- dependency behavior changed globally
- release-level validation is requested
- several subsystems were modified
- targeted tests cannot adequately bound regression risk

Do not run the full suite after every small edit.

## Failure classification

Before changing code, distinguish:

### Product/code failure

The test executes and exposes incorrect project behavior.

Action:
- investigate project code
- make the smallest justified correction

### Test failure

The implementation is correct but test expectations or setup are stale/incorrect.

Action:
- verify the intended contract
- update the test only when evidence supports it

### Environment failure

Examples:

- missing dependency
- unavailable Docker
- unavailable Redis/PostgreSQL/RabbitMQ
- wrong Python environment
- missing external executable

Action:
- report the environmental blocker
- do not rewrite working project code merely to make the local environment pass

### Collection/import failure

First determine whether the failure comes from:

- project import structure
- missing dependency
- wrong interpreter/environment
- stale test import
- packaging/configuration

Do not assume every collection failure is an application bug.

## Generated-code verification

When AutoForge generator behavior changes:

verify both:

1. generator-side unit behavior
2. generated-output contract where relevant

If a problem is found in `kis-auto-trading` and originates from AutoForge
generation:

fix AutoForge first.

Do not patch generated-owned consumer output as the primary fix.

## Test creation rules

Tests should:

- verify behavior rather than implementation trivia
- be deterministic
- avoid unnecessary sleeps
- avoid unnecessary network access
- reuse existing fixtures when appropriate
- keep test setup proportional to the behavior under test
- expose useful failure messages

Do not create tests solely to increase test count.

## Expensive validation

Before running an unusually expensive test command, ask:

1. What risk does this command verify?
2. Can a smaller command verify the same risk?
3. Has the prerequisite focused test already passed?

If a smaller command is sufficient, use it.

## Reporting

After verification, report:

- tests executed
- pass/fail result
- failures caused by environment separately
- unverified areas
- whether broader regression testing is still warranted

Do not describe an environment dependency failure as a confirmed code regression.

## Final principle

Prefer:

small change
+
focused test
+
incremental expansion

over:

large change
+
full-suite-first validation

Tests are a quality mechanism and a cost-control mechanism.
