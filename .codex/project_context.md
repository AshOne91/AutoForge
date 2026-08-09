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

## Architecture lineage and project roles

The long-term direction is inherited from three reference systems, translated
to current Python contracts rather than copied literally:

- `common-tool`: specification-driven composition of models, protocols,
  controllers, templates/modules, persistence/SQL, and applications.
- `game-server`: runtime meaning of those composed modules, including
  lifecycle, service wiring, persistence boundaries, and Global versus Shard
  data responsibilities.
- `base_server`: the Python/FastAPI translation, including routers, services,
  async lifecycle, SQL access, Redis/shared state, messaging, outbox, and
  container execution.

AutoForge is the reusable generator/control-plane project. `kis-auto-trading`
is its consumer and vertical-slice validation project. Generated-code defects
are repaired in AutoForge; KIS owns project-specific business behavior.

The intended product direction is a specification that derives a coherent
application skeleton: domain/module contracts, API or packet boundaries,
database models and reproducible SQL/migrations, shared services, and the
application composition root. Generated, scaffolded, and user-owned files must
remain distinguishable.

The historical `.codex` documents were consolidated into `AGENTS.md`, Skills,
and this context document. Their architectural intent is retained here; the
old files are not required as duplicate instructions.

## Reference usage

Use `.codex/architecture.md` only for architecture questions.
Use `.codex/current_status.md` only for implementation status.
Use `.codex/next_task.md` only for the current bounded development target.
Use `.codex/roadmap.md` only for future sequencing.

Do not load all reference documents by default.
