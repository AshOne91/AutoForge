# AutoForge Agent Instructions

## Required reading order

Before modifying code, read these files in order:

1. `.codex/bootstrap.md`
2. `.codex/project_context.md`
3. `.codex/current_status.md`
4. `.codex/architecture.md`
5. `.codex/development_rules.md`
6. `.codex/coding_style.md`
7. `.codex/common_tool_analysis.md`
8. `.codex/roadmap.md`
9. `.codex/next_task.md`

## Project constraints

- Do not redesign the architecture without explicit approval.
- Do not add unrelated features.
- Keep changes small and reviewable.
- Use Python 3.12.
- Use the `src` package layout.
- Use pytest for tests.
- Use type hints.
- Prefer composition over inheritance.
- Keep the design async-first where asynchronous behavior is relevant.
- Do not introduce global mutable state.
- Do not use `print()` in production code; use logging.
- Do not implement webhook, Git automation, AI generation, or pipeline functionality before the current stabilization work is complete.
- Preserve existing public APIs unless a change is explicitly approved.

## Required workflow

Before editing:

1. Inspect the repository tree.
2. Read `pyproject.toml`.
3. Run `git status`.
4. Run `pytest`.
5. Explain the current failures.
6. Propose a minimal plan.
7. Wait for approval before broad refactoring.

After editing:

1. Run the relevant focused tests.
2. Run the full `pytest` suite.
3. Run `python -m autoforge.main version`.
4. Show changed files.
5. Summarize remaining issues.
6. Do not commit or push unless explicitly requested.
