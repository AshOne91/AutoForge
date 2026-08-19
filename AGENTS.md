# AutoForge Agent Instructions

## Project role

AutoForge is the primary project in this workspace.

`kis-auto-trading` is a consumer/validation project. If a defect in KIS originates
from generated code, templates, manifests, or generator behavior, fix AutoForge
first instead of patching generated-owned output directly.

## Core rules

- Use Python 3.12 and the `src` package layout.
- Use pytest and type hints.
- Preserve async-first behavior where relevant.
- Prefer composition over inheritance.
- Avoid global mutable state.
- Use logging instead of `print()` in production code.
- Preserve public contracts unless explicitly approved.
- Keep changes small, bounded, and reviewable.
- Do not redesign unrelated architecture or add unrelated features.

## Context efficiency

Do not read the whole repository or all `.codex` documents by default.

Explore in this order:

1. exact request, error, or failing test
2. relevant symbol
3. references
4. relevant symbol bodies or small file sections
5. broader search only when required

Prefer Serena symbol/reference lookup when it is narrower than whole-file reading.
Do not reread information already present in context.

Files under `.codex/` are reference material. Read only the specific document
needed for the current task.

## Model routing

For substantial code-changing, debugging, or architectural tasks, use the
`model-routing` Skill under `.agents/skills/model-routing/`.

Do not load it merely for trivial reading, explanation, or mechanical edits when
routing is unnecessary.

The agent may recommend KEEP, DOWNGRADE, or UPGRADE, but cannot silently change
the user's current model or reasoning setting.

The Skill is authoritative for routing criteria, report format, and whether a
routing report requires the agent to stop. Do not duplicate those details here.

## Testing

Verify the smallest useful scope first:

focused test
→ affected module tests
→ integration tests when relevant
→ full suite only when regression risk warrants it

Every behavioral change requires appropriate verification.

## Git safety

Before modifying code, check `git status` and preserve unrelated user changes.

After a verified, bounded change, inspect the diff and automatically commit and
push each affected repository separately. Pause and report instead when
verification fails or is incomplete, ownership is unclear, unrelated changes are
present, the action is destructive, or push is rejected.

Do not stash, reset, restore, or rewrite history unless explicitly requested.

After changes, report changed files, verification performed, and remaining issues.

## Specialized workflows

Keep this file short.

Put specialized procedures in `.agents/skills/` and load them only when relevant.

For explicitly enabled unattended multi-unit work, use the
`continuous-work-session` Skill. It defines the durable checkpoint and mandatory
stop conditions; it does not relax this file's safety rules.

For documentation creation, modification, merge, move, or deletion, use the
`docs-governance` Skill. Prefer updating an existing authoritative document over
creating a new document.

## Architecture lineage

- For specification/generator/application architecture decisions rooted in common-tool, game-server, or base_server, use the `architecture-lineage` Skill.
- For feature work spanning AutoForge and consumer projects, use `autoforge-vertical-slice`: reuse existing capabilities, build one verified end-to-end slice, and extend it incrementally.
