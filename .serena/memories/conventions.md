# Conventions

- Keep changes small, bounded, and reviewable.
- Do not redesign unrelated architecture without explicit approval.
- Use Python type hints, pytest, and async patterns where I/O is involved.
- Prefer composition and dependency injection over inheritance.
- Avoid global mutable state and production `print()`; use logging.
- Use pathlib for filesystem paths where practical.
- Preserve public contracts unless a change is explicitly approved.

## Context efficiency

Explore narrowly:

symbol
→ references
→ relevant symbol bodies
→ targeted file sections
→ broader search only when required.

Use the appropriate Serena instance:
- AutoForge → `serena_autoforge`
- kis-auto-trading → `serena_kis`

Do not reread code already available in the current context.

Do not load all `.codex` documentation automatically.
Read only the specific reference needed for the bounded task.

## Testing

Use the `testing-workflow` Skill.

Prefer:
focused test
→ affected module tests
→ integration tests when relevant
→ full suite only when regression risk warrants it.

## Model routing

Use the `model-routing` Skill for substantial development tasks.
The default cost-oriented route is Luna, escalating only with concrete evidence.
