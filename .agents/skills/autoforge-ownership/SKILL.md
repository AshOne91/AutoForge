---
name: autoforge-ownership
description: Protect AutoForge-generated ownership boundaries across AutoForge and consumer projects such as kis-auto-trading. Use when modifying generated output, templates, generators, manifests, scaffolded files, consumer projects, or when deciding whether a defect should be fixed in AutoForge or in user-owned consumer code.
---

# AutoForge Ownership Workflow

## Goal

Preserve the ownership boundary between AutoForge and projects generated or
validated by AutoForge.

AutoForge is the primary source project.

Consumer projects such as `kis-auto-trading` are used to validate generated
output and application behavior.

A defect in generated output should normally be fixed at its AutoForge source,
not patched permanently in the generated consumer file.

## Ownership classes

Before modifying a file affected by AutoForge generation, classify it as one of:

1. generated-owned
2. scaffolded / generated-once
3. user-owned
4. unknown

Do not edit a file with unknown ownership until ownership has been determined.

## Source of truth

Do not infer ownership only from:

- directory name
- filename
- code style
- assumptions
- whether a file "looks generated"

Prefer explicit evidence such as:

- AutoForge manifests
- generation metadata
- generator configuration
- template definitions
- documented ownership rules
- generated-file markers
- scaffold/preserve rules

If evidence conflicts, stop and report the ambiguity before making a destructive
change.

## Generated-owned files

Generated-owned files are controlled by AutoForge.

Do not permanently hand-edit generated-owned consumer output to fix a generator
defect.

Instead:

1. reproduce or identify the consumer defect
2. determine which generated artifact is wrong
3. trace that artifact back to AutoForge
4. locate the responsible generator, template, specification, plugin, or mapping
5. fix the AutoForge source
6. run focused AutoForge tests
7. regenerate the affected consumer output
8. inspect the generated diff
9. run focused consumer validation

The generated consumer result is evidence.

AutoForge is the primary repair location.

## Scaffolded or generated-once files

Scaffolded files may become partially or fully user-maintained after initial
generation.

Before editing:

- inspect the actual preservation/scaffold rule
- identify generated-controlled versus user-controlled regions if such boundaries
  exist
- preserve user modifications
- never overwrite a scaffolded file merely because a template has changed

If AutoForge intentionally preserves the file after first generation, treat the
preserved content as user-owned unless project rules explicitly state otherwise.

## User-owned files

User-owned consumer code may be edited directly when the defect belongs to
application-specific behavior.

Examples include behavior intentionally outside generator ownership.

Do not move application-specific logic into AutoForge merely because AutoForge
exists.

AutoForge should provide reusable generation/infrastructure behavior.

Consumer projects should retain domain-specific implementation where intended.

## Unknown ownership

If ownership is uncertain:

STOP BEFORE EDITING.

Inspect the smallest relevant ownership source, such as:

- manifest entry
- generator registration
- template mapping
- scaffold rule
- project documentation

Do not perform broad repository analysis if one manifest or registration entry can
answer the question.

Report:

OWNERSHIP: UNKNOWN

and state what evidence is needed.

## Consumer defect decision

When a defect is discovered in `kis-auto-trading`, ask:

### Question 1

Was the problematic behavior produced or controlled by AutoForge?

If YES:

investigate AutoForge first.

### Question 2

Is the problem in consumer-specific business logic intentionally outside generator
ownership?

If YES:

fix the consumer project.

### Question 3

Is the file scaffolded or preserved after generation?

If YES:

inspect the preservation contract before deciding where to fix it.

Do not choose the repair location based only on convenience.

## Correct repair flow

Preferred flow for generator defects:

consumer symptom
→ generated artifact
→ ownership evidence
→ AutoForge source
→ focused AutoForge fix
→ focused AutoForge tests
→ regeneration
→ generated diff
→ focused consumer tests

Avoid:

consumer symptom
→ directly patch generated artifact
→ generator remains broken

The second flow creates drift and causes the defect to return on regeneration.

## Temporary diagnostic edits

A generated-owned consumer file may be changed temporarily only when a local
diagnostic experiment is genuinely useful.

Such a change must be treated as temporary.

Do not present it as the final repair.

After the experiment:

- revert or regenerate the temporary change
- implement the real fix in AutoForge if the hypothesis is confirmed
- verify the regenerated output

## Regeneration safety

Before regeneration:

- check Git status in the affected repository
- preserve unrelated user changes
- understand the expected generation scope
- avoid broad regeneration when a narrower generation target is available

After regeneration:

- inspect the diff
- confirm only expected files changed
- identify overwritten or preserved files
- verify generated contracts with focused tests

Do not assume successful generation means correct generation.

## AutoForge modification scope

When repairing a generator problem, prefer the narrowest responsible layer.

Examples of possible layers:

specification
→ validation
→ plugin
→ generator
→ template
→ manifest
→ generated artifact

Do not redesign the entire generation architecture for a localized template or
mapping defect.

## Testing

For an AutoForge ownership-related fix, verification normally has two levels.

### Level 1: AutoForge

Verify the generator-side behavior with the smallest relevant tests.

### Level 2: Consumer

Regenerate or validate the affected consumer artifact and run focused consumer
tests when practical.

Use the `testing-workflow` Skill for test-scope decisions.

## Git safety

Never:

- discard unrelated consumer changes
- overwrite preserved user code without evidence
- reset a repository to make generation easier
- commit generated noise without inspecting it

Before regeneration or cross-repository changes, inspect Git status in every
affected repository.

## Reporting

When ownership affects the repair, report:

OWNERSHIP:
generated-owned / scaffolded / user-owned / unknown

DEFECT SOURCE:
AutoForge / consumer / not yet determined

REPAIR LOCATION:
<where the permanent fix belongs>

VERIFICATION:
<AutoForge test and/or consumer validation>

If a generated consumer file was temporarily edited, explicitly state that the
edit is diagnostic and not the permanent repair.

## Final principle

Generated output is not the primary source of truth for generator behavior.

For generator-owned behavior:

fix the source
→ regenerate
→ verify

Do not create permanent drift between AutoForge and its generated consumers.
