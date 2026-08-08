---
name: code-review-graph
description: Use code-review-graph for blast-radius analysis, review context, multi-hop dependency traversal, change impact, and AutoForge/KIS cross-repository analysis. Use when direct symbol lookup is insufficient and graph-level relationships are needed.
---

# Code Review Graph Workflow

## Purpose

Use CRG only for graph-level questions.

Do not use CRG for ordinary symbol lookup when Serena can answer more narrowly.

Primary division of responsibility:

Serena
→ exact symbol
→ direct references
→ symbol bodies
→ diagnostics

CRG
→ minimal graph context
→ blast radius
→ review context
→ change impact
→ multi-hop traversal
→ cross-repository relationships

## Deferred tool behavior

CRG is registered as the MCP server:

`crg`

Its tools may be deferred and therefore may not appear in the ordinary callable
tool list.

Do NOT conclude that CRG is unavailable merely because `mcp__crg` is absent from
the immediately visible tool surface.

If `/mcp` shows `crg` enabled, search the actual deferred `ALL_TOOLS` collection
for the required CRG tool.

Known CRG tools:

- `mcp__crg__get_minimal_context_tool`
- `mcp__crg__get_impact_radius_tool`
- `mcp__crg__get_review_context_tool`
- `mcp__crg__query_graph_tool`
- `mcp__crg__detect_changes_tool`
- `mcp__crg__traverse_graph_tool`
- `mcp__crg__cross_repo_search_tool`

Use the exact callable tool from `ALL_TOOLS`.

Do not repeatedly rediscover these names once they are available in the current
session.

## Tool selection

### Minimal context

Use:

`get_minimal_context_tool`

when a bounded change requires graph-aware context but a broad dependency analysis
is unnecessary.

Prefer this before larger graph exploration when sufficient.

### Symbol relationships

Use:

`query_graph_tool`

for graph relationships around a known symbol or file.

Supported patterns include:

- callers_of
- references_to
- callees_of
- imports_of
- importers_of
- children_of
- tests_for
- inheritors_of
- file_summary

Use this when the question names a specific symbol such as
`PluginManager.execute`.

Prefer Serena when only exact direct references are needed.
Prefer CRG query_graph when graph-aware callers/tests/relationships are useful.

### Impact radius

Use:

`get_impact_radius_tool`

for FILE-LEVEL blast-radius analysis.

It accepts changed files, not a symbol name.

Do not pass a class or method such as `PluginManager.execute`
as `changed_files`.

If the user asks about hypothetical impact of a symbol:

1. locate its defining file with Serena if needed
2. use `query_graph_tool` for symbol relationships
3. use `traverse_graph_tool` for wider multi-hop relationships
4. use `get_impact_radius_tool` only when file-level impact is desired

### Review context

Use:

`get_review_context_tool`

when reviewing a meaningful change or diff and graph context can identify affected
callers, tests, or neighboring components.

Do not run a graph review automatically after every small passing change.

### Detect changes

Use:

`detect_changes_tool`

for graph-backed analysis of current repository changes.

Use when the current diff is meaningful enough that structural impact matters.

Do not use for trivial documentation or formatting changes.

### Graph traversal

Use:

`traverse_graph_tool`

when a relationship requires multiple hops and Serena direct references are no
longer sufficient.

Examples:

caller
→ service
→ pipeline
→ downstream handler

Avoid large-depth traversal without a concrete question.

### Cross-repository search

Use:

`cross_repo_search_tool`

only when the problem genuinely crosses:

AutoForge
↔
kis-auto-trading

Typical case:

a generated behavior observed in KIS must be traced back toward its AutoForge
source or related concepts must be compared across both repositories.

For simple repository-local work, do not use cross-repo search.

## Repository roles

AutoForge:

`C:\AutoForge`

Primary generator/framework repository.

kis-auto-trading:

`C:\kis-auto-trading`

Consumer/validation repository.

Both repositories have CRG graphs.

Use `autoforge-ownership` when determining where the permanent repair belongs.

## Serena before CRG

For a normal bug or feature:

1. start from the exact error/request
2. use the appropriate Serena instance
3. locate the exact symbol/direct references
4. use CRG only if wider structural impact remains unresolved

Do not call Serena and CRG with the same simple query merely for confirmation.

## Context economy

CRG is intended to reduce repository context.

Do not respond to a small CRG result by reading every implicated file.

Use graph results to choose the smallest next code-reading step.

Preferred flow:

bounded question
→ CRG result
→ 1-3 relevant symbols/files
→ focused verification

Avoid:

CRG result
→ entire repository scan

## Graph freshness

The graph is persistent and may become stale after code changes.

Before relying on CRG for important impact/review analysis after source changes,
ensure the affected repository graph is current.

Prefer incremental update rather than a full rebuild when possible.

Do not rebuild the complete graph after every edit.

## Cost policy

CRG tools are intentionally deferred.

Do not disable MCP deferral merely to make CRG tools permanently visible unless
there is a demonstrated workflow problem that cannot be solved through deferred
tool discovery.

Permanent tool exposure increases the always-available tool surface.

Use deferred discovery to preserve context efficiency.

## Final rule

Use:

Serena for precision.

CRG for relationships.

Tests for proof.

Do not use a broader tool when a narrower one already answers the question.

## CRG Target and Schema Rules

### Symbol targets

For `query_graph_tool`, prefer an exact CRG qualified target.

Preferred form:

`relative/path.py::Class.method`

or:

`relative/path.py::function`

Example:

`src/autoforge/core/plugin/manager.py::PluginManager.execute`

Do not assume a bare symbol such as:

`PluginManager.execute`

will resolve correctly.

When the exact path is unknown:

1. use the appropriate Serena instance to locate the symbol
2. obtain its repository-relative file path
3. construct the qualified CRG target
4. call CRG only for the graph relationship that is actually needed

### query_graph_tool

Use `query_graph_tool` for graph relationships around an exact node.

Typical patterns:

- `callers_of`
- `references_to`
- `callees_of`
- `tests_for`
- other relationships supported by the current CRG tool schema

A `tests_for` result of zero means only that CRG has no matching test relationship
for that graph node.

It does NOT prove that no tests exist in the repository.

Use the `testing-workflow` Skill or targeted Serena/test search when actual test
coverage must be established.

### get_impact_radius_tool

`get_impact_radius_tool` is file-oriented.

Pass repository-relative changed file paths.

Correct example:

`src/autoforge/core/plugin/manager.py`

Do NOT pass:

`PluginManager.execute`

as a changed file.

For a symbol-level impact question:

1. Serena locates the exact symbol/file
2. `query_graph_tool` checks graph relationships
3. `traverse_graph_tool` may expand multi-hop relationships
4. `get_impact_radius_tool` is used only when file-level blast radius is useful

### Evidence rule

Do not interpret an empty CRG relation more broadly than the tool result supports.

Examples:

- zero callers != symbol is unused in every possible runtime path
- zero tests != repository has no tests
- zero file impact != symbol has no semantic importance

Treat CRG as structural graph evidence and combine it with focused code/test
verification when correctness requires it.
