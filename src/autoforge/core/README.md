# Core

AutoForge의 인프라 독립적인 핵심 계약과 모델을 둔다.

- Config
- Context
- EventBus
- Generation 계약과 Hash
- Pipeline 계약
- Plugin Framework
- Registry
- Specification과 공통 Type System
- Task
- Workspace 경로 안전 경계

구체적인 FastAPI Generator와 검증 Service, 파일시스템·Git·HTTP Adapter는 Core
밖에 둔다. 전체 계층 계약은
[`system_design.md`](../../../docs/architecture/system_design.md)를 따른다.
