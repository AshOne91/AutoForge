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

Before every substantial task, report the current model/reasoning, recommended
routing, and KEEP/DOWNGRADE/UPGRADE decision. After reporting, stop and wait for
the user's separate follow-up approval before beginning work. Always stop after
the routing report, even if the original request also contains an affirmative
instruction or the recommendation is KEEP.

## Testing

Verify the smallest useful scope first:

focused test
→ affected module tests
→ integration tests when relevant
→ full suite only when regression risk warrants it

Every behavioral change requires appropriate verification.

## Git safety

Before modifying code, check `git status` and preserve unrelated user changes.

Do not commit, push, stash, reset, restore, or rewrite history unless explicitly
requested.

After changes, report changed files, verification performed, and remaining issues.

## Specialized workflows

Keep this file short.

Put specialized procedures in `.agents/skills/` and load them only when relevant.

## Architecture lineage

- For specification/generator/application architecture decisions rooted in common-tool, game-server, or base_server, use the `architecture-lineage` Skill.
