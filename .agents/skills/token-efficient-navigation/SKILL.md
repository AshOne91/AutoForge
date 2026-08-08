---
name: token-efficient-navigation
description: Explore AutoForge and related consumer repositories with minimal context and tool usage. Use when locating code, tracing symbols or references, investigating errors, determining change impact, or deciding between Serena, text search, and code-review-graph.
---

# Token-Efficient Code Navigation

## Goal

Find enough evidence to complete the bounded task while reading the minimum
necessary repository context.

More context is not automatically better.

Stop exploring once enough evidence exists to make the next safe decision.

## First rule

Use information already present in the current context before calling another tool.

Do not reread:

- files already inspected
- symbols already available
- test failures already shown
- documentation already loaded
- tool results that already answer the question

## Exploration order

Prefer this sequence:

1. exact user request or error
2. exact symbol or identifier
3. direct references
4. relevant symbol body
5. small surrounding file section
6. exact text search
7. related file
8. dependency/impact graph when needed
9. broader repository search
10. whole-file or repository-wide reading only as a last resort

Expand gradually.

Do not begin with repository-wide analysis for a localized task.

## Serena

Prefer Serena when the question is symbol-oriented.

Good Serena targets include:

- class definition
- function definition
- method definition
- symbol overview
- callers
- references
- inheritance/implementation relationships
- a specific execution path involving known symbols

Examples:

- find `PluginManager`
- find references to `Registry.list`
- locate `EventBus.publish`
- inspect callers of `GenerationWorker._push_validated`

Prefer:

symbol
→ references
→ relevant symbol bodies

Do not automatically read the entire containing file after a successful symbol
lookup.

## Text search

Prefer normal text search when the target is not primarily a code symbol.

Good text-search targets include:

- exact error messages
- configuration keys
- YAML/TOML/JSON
- SQL
- migrations
- documentation
- comments
- log messages
- CLI strings
- filenames
- environment variables

Do not force Serena onto content that ordinary text search can locate more cheaply.

## code-review-graph

When code-review-graph is installed, reserve it primarily for questions involving
relationships beyond a simple direct symbol lookup.

Good graph-oriented questions include:

- multi-hop dependency impact
- blast radius
- change impact across modules
- review context for a nontrivial diff
- identifying downstream dependents
- understanding a broader dependency chain

Do NOT use code-review-graph merely to find one known class or function when
Serena can answer directly.

Do NOT call both Serena and code-review-graph for the same simple lookup merely
for confirmation.

Use both only when they answer different questions.

Example:

Serena:
"Where is PluginManager.execute defined and directly referenced?"

code-review-graph:
"What wider components may be affected if PluginManager execution semantics
change?"

## Tool selection rule

Choose the narrowest useful tool.

Use:

CURRENT CONTEXT
when the answer is already available.

SERENA
for symbol-level navigation and direct references.

TEXT SEARCH
for strings, config, SQL, docs, errors, and non-symbol content.

CODE-REVIEW-GRAPH
for multi-hop dependency or blast-radius analysis after it is installed.

Do not choose a more expensive or broader tool merely because it is available.

## Search budget

For a normal bounded task, begin with approximately:

- 1-3 relevant symbols
- 1-2 relevant files or small sections
- one focused failing test or error path

These are starting limits, not rigid correctness limits.

Expand only when existing evidence is insufficient.

Before expanding, state internally what unanswered question requires more context.

## Whole-file reading

Read an entire large file only when:

- the behavior cannot be understood from relevant symbols/sections
- ordering across the file matters
- module-level initialization matters
- definitions are tightly coupled across the file
- the file itself is small enough that targeted reading provides little benefit

Do not read an entire file simply because it contains a relevant symbol.

## Repository-wide analysis

Repository-wide analysis is exceptional.

Use it only when:

- architecture-wide understanding is explicitly requested
- the failure genuinely spans unknown subsystems
- targeted search repeatedly fails
- a major cross-cutting change requires it

Do not perform repository-wide analysis for:

- a localized test failure
- a rename
- one generator
- one plugin
- one API endpoint
- one known stack trace

## AutoForge and kis-auto-trading

Always identify which repository owns the current problem.

AutoForge is primary.

`kis-auto-trading` is a consumer/validation project.

If KIS exposes a generated-code defect:

1. inspect the generated symptom narrowly
2. determine ownership
3. trace the responsible source into AutoForge
4. continue investigation in AutoForge

Use the `autoforge-ownership` Skill when ownership is relevant.

Do not deeply inspect both repositories by default.

Cross-repository exploration must have a concrete reason.

## Generated artifacts

Avoid exploring generated output broadly when the source generator or template can
answer the question more directly.

Generated output is useful for:

- confirming a symptom
- comparing expected versus actual output
- validating regeneration

It is usually not the best place to understand generator architecture.

## Errors and failures

Begin from the exact error.

Preferred flow:

error
→ failing test
→ implicated symbol
→ direct caller/reference
→ smallest responsible code path

Avoid:

error
→ scan entire repository
→ load architecture docs
→ read every related-looking module

## Documentation

Do not load all `.codex` documents automatically.

Read a document only when it answers a concrete unresolved question.

Examples:

- architecture question → `architecture.md`
- current implementation status → `current_status.md`
- documented next work → `next_task.md`
- future sequencing → `roadmap.md`

Stop reading once the needed information is found.

## Duplicate exploration

Before another tool call, ask:

"Do I already have this information?"

If YES:

do not retrieve it again.

If partially known:

retrieve only the missing portion.

## Model and cache efficiency

Avoid repeatedly changing model simply because exploration moved to another file.

Keep a coherent bounded investigation on one sufficient model when practical.

Reducing context and duplicate retrieval usually saves more than repeatedly
restarting exploration on different models.

Use the `model-routing` Skill for actual model-selection decisions.

## Completion condition

Navigation is complete when there is enough evidence to answer:

- what needs to change
- where it needs to change
- why that location is responsible
- what focused verification is required

Do not continue exploring merely to increase confidence after these questions are
adequately answered.

## Reporting

For nontrivial investigations, summarize only useful findings:

EXPLORED:
- relevant symbols/files only

FOUND:
- responsible path

NOT EXPLORED:
- important areas intentionally left untouched, if relevant

NEXT:
- smallest justified implementation or verification step

Do not dump large search results into the final response.

## Final principle

Prefer:

existing context
→ precise lookup
→ direct references
→ targeted code
→ focused verification

before:

broad search
→ entire files
→ repository-wide analysis

The objective is minimum sufficient context, not maximum repository awareness.

## Workspace Serena Routing

This workspace contains two repositories with dedicated Serena MCP instances.

### AutoForge

For symbol-oriented work in AutoForge, use:

- `mcp__serena_autoforge__find_symbol`
- `mcp__serena_autoforge__find_referencing_symbols`
- `mcp__serena_autoforge__get_symbols_overview`
- other `mcp__serena_autoforge__*` tools only when required

Primary repository:

`C:\AutoForge`

### kis-auto-trading

For symbol-oriented work in kis-auto-trading, use:

- `mcp__serena_kis__find_symbol`
- `mcp__serena_kis__find_referencing_symbols`
- `mcp__serena_kis__get_symbols_overview`
- other `mcp__serena_kis__*` tools only when required

Consumer repository:

`C:\kis-auto-trading`

### Selection rules

Use exactly one Serena instance for ordinary repository-local navigation.

AutoForge task:
→ use `serena_autoforge`

KIS task:
→ use `serena_kis`

Do not call both Serena instances for the same simple symbol lookup.

Do not ask whether Serena is available when the corresponding MCP namespace is
already exposed in the current tool surface.

Prefer actual tool-surface evidence over assumptions about MCP availability.

### Cross-repository defects

When a defect appears in kis-auto-trading:

1. use `serena_kis` only to locate and bound the symptom
2. determine ownership
3. if AutoForge-generated behavior is responsible, stop treating the generated
   KIS artifact as the repair location
4. switch investigation to `serena_autoforge`
5. locate the responsible generator/template/specification/plugin
6. repair AutoForge
7. regenerate and verify KIS

Use the `autoforge-ownership` Skill for the ownership decision.

Do not deeply explore both repositories unless the task genuinely crosses the
generation boundary.

### Serena initialization

The Serena instances are configured with their projects at MCP server startup.

Therefore, do not call `activate_project` for ordinary AutoForge or KIS work unless
the active project is demonstrably incorrect.

Do not perform onboarding repeatedly.

Do not call `initial_instructions` repeatedly in the same coherent session after
the required Serena instructions are already known.

### Cost rule

Serena exists to reduce context consumption.

Do not turn a narrow symbol lookup into:

- repository-wide scanning
- entire-file reading
- duplicate searches in both repositories
- repeated symbol lookups for information already in context

Stop retrieving context once enough evidence exists for the next safe action.
