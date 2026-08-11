---
name: architecture-lineage
description: Use when changing AutoForge specifications, generators, module/application composition, lifecycle, persistence boundaries, Global/Shard routing, or when architectural intent must be compared with common-tool, game-server, or base_server.
---

# AutoForge Architecture Lineage

AutoForge has three important historical/reference systems.

They are architectural references, not repositories to copy literally.

## Canonical Reference Paths

### common-tool

Canonical local path:

`C:\게임베이스툴\common-tool-master`

Role:

- historical specification-driven architecture generator
- architectural ancestor of AutoForge
- describes how one validated specification can derive connected artifacts
- useful for understanding Model, Protocol, Controller, Template, DB, SQL,
  Service, and Application composition concepts

Conceptual flow:

specification
→ models/protocols
→ controllers
→ templates/modules
→ persistence/SQL
→ application composition

Important:

`common-tool` was more than a text-template generator.

Its important inheritance for AutoForge is the idea that one specification
describes connected architecture and generators derive consistent artifacts
from that source.

Do not port the historical C# implementation literally.

---

### game-server

Canonical local path:

`C:\게임베이스서버\game-server-master`

Role:

- runtime reference corresponding to common-tool architectural concepts
- demonstrates the runtime meaning of Application, Service, Template,
  lifecycle, persistence, and composition
- useful when common-tool generation intent alone is insufficient

Important interpretation:

A historical `Template` is not merely a text template.

It can represent a reusable runtime/business module that owns concepts such as:

- state
- lifecycle
- persistence boundaries
- role-specific behavior
- module wiring

Applications act as composition roots by selecting and wiring required
Services and Templates.

Important inherited principles include:

- explicit module composition
- deterministic generated wiring
- lifecycle-aware modules
- aggregate-oriented persistence boundaries
- separation of Global data and user/shard data
- separation of generated code and developer extension points

Do not confuse this historical repository with generated test/example packages
named `game_server` inside AutoForge.

Historical reference:

`C:\게임베이스서버\game-server-master`

Generated/example package names such as:

`game_server`

are different concepts.

---

### base_server

Canonical local path:

`C:\SKN12-FINAL-2TEAM\base_server`

Role:

- later Python/FastAPI reference implementation and experiment
- bridge between the older C#/game-server architecture and the current
  Python AutoForge direction
- useful for understanding modern Python backend equivalents

Relevant concepts include:

- FastAPI application composition
- Router / Service / Domain boundaries
- asynchronous application lifecycle
- database access
- Global / Shard responsibilities
- Redis/shared state
- RabbitMQ/message processing
- Transactional Outbox concepts
- Docker/container execution
- proxy/instance routing concepts

Important:

`base_server` is reference material.

It is NOT the current AutoForge implementation target and is NOT the current
KIS product code.

Do not copy its implementation automatically.

---

## Current AutoForge Reference

Primary repository:

`C:\AutoForge`

Detailed historical architecture analysis:

`C:\AutoForge\docs\reference\common_tool_analysis.md`

Use that analysis before opening the external historical repositories when it
already answers the architectural question.

Current AutoForge contracts and tests remain authoritative.

---

## Current Consumer / Validation Repository

KIS repository:

`C:\kis-auto-trading`

KIS is the primary vertical-slice consumer used to validate whether AutoForge
generated architecture works in a real project.

When KIS exposes a defect:

1. determine ownership
2. if AutoForge owns the generated behavior, fix AutoForge
3. regenerate or verify generated output
4. validate the result in KIS

Do not permanently patch AutoForge-owned generated code only inside KIS.

---

## Reference Priority

For architecture decisions, use this priority:

1. Current AutoForge contracts and tests
2. Current KIS vertical-slice requirements
3. `common-tool` for historical generation intent
4. `game-server` for historical runtime meaning
5. `base_server` for later Python/FastAPI implementation ideas

Historical repositories inform the design.

They do not override current validated contracts.

---

## When To Use These References

Use this Skill for changes involving:

- ProjectSpec / ModuleSpec evolution
- generator architecture
- Application composition
- Service dependencies
- module lifecycle
- persistence ownership
- aggregate load/save boundaries
- Global versus Shard responsibilities
- message/event contracts
- generated versus scaffolded extension boundaries
- major architecture restructuring

Do NOT load these historical references for ordinary bounded implementation
tasks such as:

- formatting
- simple bug fixes
- isolated unit tests
- a known Dockerfile rendering change
- trivial symbol lookup

This prevents unnecessary context/token usage.

---

## Navigation Policy

Start narrow.

Preferred order:

1. current task/context
2. current AutoForge symbol using Serena
3. current KIS symbol when validating consumer behavior
4. `docs/reference/common_tool_analysis.md`
5. exact relevant location in external historical repository

Never scan all three historical repositories simply because this Skill was
activated.

Use only the reference necessary to answer the architectural question.

---

## Historical-to-Modern Translation Rule

Preserve architectural intent, not implementation technology.

Prefer current AutoForge equivalents such as:

- deterministic specification-driven generation
- GENERATED / SCAFFOLDED / USER_OWNED ownership
- explicit FastAPI composition
- dependency providers
- lifespan-based lifecycle
- async-first I/O
- SQLAlchemy/database plugins
- migration history
- explicit Global/Shard routing
- external shared state such as Redis
- HTTP/WebSocket/Queue transport contracts

Do not recreate historical infrastructure merely because it existed.

A historical capability should enter current AutoForge only when a real
vertical slice or explicit requirement demonstrates the need.

---

## Final Principle

common-tool explains:

WHY and WHAT should be generated.

game-server explains:

WHAT those generated concepts mean at runtime.

base_server explains:

HOW related ideas were later explored in Python/FastAPI.

AutoForge decides:

HOW those principles should be implemented today.
