# AutoForge Project Context

AutoForge is the primary repository.

It is a specification-driven Python automation platform that generates and
validates modular FastAPI projects and can safely automate Git-based workflows.

## Repository roles

- AutoForge owns specifications, generators, plugins, manifests, validation,
  automation contracts, and reusable infrastructure.
- `kis-auto-trading` is the first consumer/validation repository.
- Generated-code defects observed in KIS must be traced back to AutoForge when
  AutoForge owns the generated behavior.
- Project-specific KIS business logic remains KIS-owned.

## Core principles

- Python 3.12, `src` layout, pytest, type hints.
- Async-first where I/O is involved.
- Deterministic generation and explicit ownership.
- Generated, scaffolded, and user-owned files must remain distinguishable.
- Validation must succeed before Git mutation.
- EventBus is generic dispatch; Pipeline owns ordered workflow.
- Plugins extend validated capabilities and should not contain project-specific logic.
- Prefer external infrastructure adapters over global mutable service state.

## Main execution model

ProjectSpec
→ GenerationPlan
→ Generator
→ Manifest
→ Validation
→ optional Git branch/commit/push/PR

Remote jobs run in isolated workspaces.

## Reference usage

Use `.codex/architecture.md` only for architecture questions.
Use `.codex/current_status.md` only for implementation status.
Use `.codex/next_task.md` only for the current bounded development target.
Use `.codex/roadmap.md` only for future sequencing.

Do not load all reference documents by default.