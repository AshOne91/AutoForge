# Core

AutoForge is the primary project.

`kis-auto-trading` is a consumer/validation repository used to verify generated
output and infrastructure behavior.

## Primary flow

validated specification
→ generation plan
→ generator/plugin
→ isolated workspace
→ manifest
→ validation
→ optional Git automation

## Architectural boundaries

- EventBus provides generic asynchronous dispatch.
- Workflow handlers own workflow logic.
- Pipeline owns task ordering, retry, timeout, and cancellation.
- Generators do not perform Git operations.
- Generated output must remain inside the job workspace.
- Validation failure blocks Git mutation.
- AutoForge owns reusable generation and infrastructure contracts.
- Consumer repositories own intended domain/business logic.

## Ownership

When a defect in kis-auto-trading originates from AutoForge-generated behavior:

consumer symptom
→ determine ownership
→ locate AutoForge source
→ fix AutoForge
→ regenerate
→ verify consumer output

Use the `autoforge-ownership` Skill for detailed ownership decisions.

## Detailed references

Use `.codex/architecture.md` only when architecture detail is required.
Use `.codex/current_status.md` only when current implementation detail is required.
Use `.codex/roadmap.md` only when future sequencing is required.
