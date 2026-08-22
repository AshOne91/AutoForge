---
name: continuous-work-session
description: Run explicitly enabled unattended AutoForge development as verified, bounded work units. Use when the user asks Codex to keep working across tasks, overnight, or until a stop condition; also use when the user enables or disables continuous-work mode.
---

# Continuous Work Session

## Overview

Keep progress durable and scoped during long autonomous work. This mode changes
when the agent pauses; it does not waive ownership, test, Git, or safety rules.

## Modes

- **ON** - continue to the next bounded unit after each verified commit and
  push. Emit a compact checkpoint, but do not wait for a reply.
- **OFF** - finish the current safe unit, report, and return to the ordinary
  request/response workflow. This is the default outside an explicit ON request.
- A direct user instruction to stop, pause, change scope, or disable the mode
  takes effect at the next safe boundary immediately.

Do not treat silence as permission to expand scope. Continue only along the
documented next task or the current user objective.

## Work Loop

For every unit:

1. Restate internally the current objective, ownership boundary, and one
   smallest deliverable. Read the existing next-task/status source only when
   needed to recover that context.
2. Check Git status before a mutation. Preserve unrelated changes. Determine
   generated, scaffolded, or user-owned ownership before edits.
3. Implement one vertical slice or repair; reuse existing contracts before
   adding a new abstraction.
4. Run focused verification, inspect the affected diff and generated outputs,
   then expand verification only when its risk requires it.
5. Update the existing status and next-task owners when a completed slice
   changes implemented state or the immediate next executable unit. Do not log
   transient investigation noise.
6. Commit and push each affected repository separately when verification is
   complete. Report the completed unit, checks, commit, and next unit.
7. In ON mode, begin only that next unit. Never silently combine several
   planned units into one large change.

## Mandatory Stop Conditions

Stop and report instead of starting another unit when any of these occurs:

- focused or broader verification fails or is incomplete;
- generated output has an unexpected diff, protected/scaffolded-file conflict,
  or unclear ownership;
- the next step changes the approved objective, transaction/sharding/security
  guarantee, or requires a new architecture decision;
- a live external action, secret, destructive change, new authority, or denied
  escalation is required.

Do not stop merely because a normal command needs an allowed tool approval.
Request the approval and continue if it is granted.

If an authorized write to a consumer repository outside the workspace fails with
`Permission denied`, treat sandbox scope as the first hypothesis. Retry the
same bounded command with scoped escalation before diagnosing a file lock or
product failure. Stop only if that retry fails or escalation is denied.

## Memory Guard

Use the commit history plus the existing status/next-task documents as durable
checkpoints. Before selecting a new unit after a commit, compare it against the
last checkpoint and current objective. Do not resume an old exploratory branch,
repeat a completed fix, or infer a broader goal from stale conversation context.

## Delivery Scope Gate

Before every new unit, identify the active delivery gate in `.codex/roadmap.md`.
It outranks `.codex/next_task.md`, old commits, and inferred opportunity.

- Start only a unit explicitly allowed by that gate.
- If `next_task.md` names work outside the gate, replace it with the smallest
  allowed unit before implementation; do not perform the stale task first.
- A consumer repository may be changed only for the gate's validation purpose.
  Do not add its business entities, routes, specifications, migrations, or
  provider workflows unless the gate explicitly permits consumer-domain work.
- Leave the gate only after its recorded completion evidence exists and the user
  explicitly authorizes the phase change. Do not infer that authorization from
  a request to continue, an unfinished roadmap item, or a convenient next task.

## Model Routing

When routing is required, use the `model-routing` Skill. Its
`Continuous-work session integration` section is authoritative for whether
KEEP, DOWNGRADE, UPGRADE, or model unavailability pauses ON-mode work.
