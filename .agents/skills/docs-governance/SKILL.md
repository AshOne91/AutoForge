---
name: docs-governance
description: Govern AutoForge documentation ownership and lifecycle. Use when creating, modifying, merging, moving, renaming, or deleting Markdown documentation, or when updating architecture, status, roadmap, next-task, guide, study, reference, README, or Serena memory content that could affect a source of truth.
---

# AutoForge Documentation Governance

## Goal

Preserve one authoritative source for each fact.

Prefer updating the existing owner over creating another document. A Guide,
Study, Reference, README, or Serena memory may summarize a fact, but it must link
to or name the authoritative source instead of redefining the contract.

## Workflow

Before changing documentation:

1. Identify the fact and its document role.
2. Search for an existing Canonical, Guide, Study, Reference, or README owner.
3. Update the existing owner when one exists.
4. Verify code claims with targeted symbols, module paths, tests, or runtime
   contracts when the document describes current implementation behavior.
5. Keep non-authoritative documents explanatory and point them to the owner.
6. Validate links, paths, ownership, and formatting after the change.

Do not scan the whole repository when targeted inspection is sufficient. Use
`token-efficient-navigation` for search scope and tool selection.

## Sources of Truth

### Canonical architecture

These files each own one current architectural concern:

- `docs/architecture/system_design.md`
- `docs/architecture/generation_contract.md`
- `docs/architecture/specification_design.md`
- `docs/architecture/database_generation.md`
- `docs/architecture/event_driven_architecture.md`
- `docs/architecture/plugin_system.md`
- `docs/architecture/control_plane_persistence.md`
- `docs/architecture/git_automation.md`
- `docs/architecture/redis_services.md`
- `docs/architecture/docker_build_contract.md`
- `docs/architecture/configuration_and_storage_policy.md`
- `docs/architecture/environment_validation_contract.md`
- `docs/architecture/observability_generation.md`
- `docs/architecture/local_port_policy.md`

Do not make a Guide, Study, Reference, README, status file, or memory an
independent owner of these contracts.

### Operational state

- `.codex/current_status.md` owns currently implemented and verified behavior and
  known current limitations.
- `.codex/roadmap.md` owns unimplemented goals, future direction, and planned
  capabilities.
- `.codex/next_task.md` owns the next single or very small execution unit.

Do not use Current Status for a full completion history, future plans, or long
design explanations. Do not use Roadmap for completed work, implemented-feature
inventories, or current Architecture contracts. Do not accumulate completed work
in Next Task, and do not merge these three roles.

### Agent policy

- `AGENTS.md` owns repository-wide principles and short Skill triggers.
- `.agents/skills/**` owns specialized execution procedures.

Keep detailed documentation governance here instead of copying it into
`AGENTS.md`.

### Derived memory

Treat `.serena/memories/**` as derived memory, never as an authoritative source.
When memory conflicts with Canonical Architecture, `AGENTS.md`, or a Skill,
correct the memory rather than the authoritative source.

## Role Boundaries

### Project entry

Keep `README.md` focused on project introduction, quick start, and a high-level
feature summary. Link to Canonical Architecture instead of defining detailed
contracts there.

### Architecture

Use Architecture documents for current:

- structure
- responsibilities and boundaries
- contracts and guarantees
- relationships
- data and control flow

Do not accumulate implementation percentages, next tasks, development logs,
dated status, completion checklists, long-term roadmap items, or retrospectives in
Architecture.

Treat a new file under `docs/architecture/` as an exception. Create one only when
all of the following are true:

1. None of the existing Canonical concerns can own it naturally.
2. It has an independent responsibility and lifecycle.
3. It is important enough that otherwise it would be repeated across documents.
4. The value of a new authoritative source exceeds the cost of another owner.

Otherwise update the existing Canonical document.

### ADR

Create an ADR only when real alternatives existed, the decision has lasting
architectural impact, future developers need its rationale, and reversing it
would have meaningful consequences.

Keep current structure in Architecture and decision rationale in ADR. Do not
create an ADR for every implementation detail or small operating rule.

### Reference

Use Reference for historical projects, external systems, comparisons, snapshots,
and target blueprints. Mark Reference or Snapshot status clearly so readers do
not mistake it for the current architecture.

Use `architecture-lineage` when historical intent from common-tool, game-server,
or base_server is required.

### Study

Use Study for learning-oriented explanations. Do not independently define
Architecture contracts, Plugin APIs, Event/Pipeline guarantees, Specification
fields, ownership policy, current status, or Next Task. Point to the applicable
authoritative source.

### Guide

Use Guide for installation, execution, testing, development, and environment
procedures. Do not redefine Agent Policy or Architecture.

## Prohibited Document Proliferation

Do not create version-copy names such as:

- `*_v2.md`, `*_v3.md`
- `*_final.md`, `*_latest.md`, `*_new.md`, `*_updated.md`
- `*_master.md`, `*_ultimate.md`, `*_copy.md`

Do not bypass this rule with an equivalent suffix. Update the existing document
and use Git history. Create a dated or versioned snapshot only when the date or
version is meaningful, and mark it explicitly as non-authoritative.

Do not create completion-summary files such as:

- `IMPLEMENTATION_COMPLETE.md`
- `REFACTOR_SUMMARY.md`
- `ARCHITECTURE_UPDATE.md`
- `PHASE_1_COMPLETE.md`
- `FINAL_REPORT.md`

Report ordinary work through the diff, commit, PR, or conversation. Preserve
durable project knowledge only by updating its proper existing owner.

## Move and Delete Safety

When moving or renaming a document:

1. Check inbound and outbound Markdown links.
2. Check references from Agent Skills, README files, and `.codex` documents.
3. Update stale paths.
4. Do not retain duplicate copies at old and new paths.

Before deleting a document, confirm that important content remains with another
owner, the file has no independent role, inbound references are gone, and Git
history is sufficient. If ownership is ambiguous, do not delete it.

## Generated Documentation

Keep generated documentation distinct from human-maintained Canonical
Architecture. Require a clear generator, regeneration procedure, generated
ownership marker, and no direct human editing.

## Skill Boundaries

- Use `architecture-lineage` for historical architecture and reference-project
  intent.
- Use `autoforge-ownership` for generated, scaffolded, and user-owned artifact
  boundaries.
- Use `token-efficient-navigation` for targeted discovery.
- Use `testing-workflow` when code behavior or tests are affected.
- Use `model-routing` for model and reasoning selection.
- Use `code-review-graph` only for graph-level change impact.

Do not copy those Skills' procedures into this Skill.

## Validation

After a documentation change that affects structure or ownership, check:

- broken Markdown links
- stale file paths and moved-file old paths
- duplicate headings
- prohibited version-copy names
- duplicate authoritative ownership
- `git diff --check`

When Architecture or code facts change, compare the relevant claims with targeted
code and tests. Do not run unrelated tests for a documentation-only change.

## Reporting

Do not create a separate Markdown report. Report in the conversation:

- modified, moved, and deleted files
- Source-of-Truth changes
- validation results
- remaining issues
