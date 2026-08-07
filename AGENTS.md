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

## Token and context efficiency

- Prefer Serena semantic tools for source exploration: symbol overview, symbol lookup, references, then only the required symbol bodies.
- Do not read an entire large source file when a targeted symbol body is sufficient.
- Use repository-wide text search only when semantic tools cannot locate the target; expand the search scope gradually.
- Do not repeatedly read code that is already present in the current context.
- Exclude unrelated or generated paths unless they are required: `.git`, `.venv`, `__pycache__`, `.pytest_cache`, `build`, `dist`, `coverage`, and generated artifacts.
- For bugs, begin with the exact error, failing test, symbol, or call path.

## Model routing gate

- Before every new implementation or code-changing task, report the task, difficulty, recommended model, recommended reasoning level, and current setting.
- Do not infer the current model or reasoning level from stale conversation context. If the current setting is not confirmed, ask the user to confirm it before editing.
- If a model or reasoning change is recommended, stop before editing and wait until the user confirms the change.
- When the confirmed current setting is suitable and the user has said to proceed, continue without asking for duplicate approval.
- Follow `docs/development/model_routing.md` for the detailed routing policy and report format.

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
