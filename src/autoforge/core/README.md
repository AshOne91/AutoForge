# Core

AutoForge의 핵심 엔진.

현재 다음 책임을 포함한다.

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

구체적인 FastAPI Generator, 파일시스템 적용, Git 공급자와 Webhook은 각
구현 단계에서 Core 계약과 분리된 계층에 추가한다.
