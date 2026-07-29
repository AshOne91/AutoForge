# AutoForge 명세 설계

## 명세 계층

AutoForge 명세는 하나의 거대한 파일에 모든 내용을 넣지 않는다.

```text
ProjectSpec
├── ApplicationSpec
├── ModuleSpec 목록
│   ├── ModelSpec
│   ├── EndpointSpec 또는 MessageSpec
│   └── DatabaseSpec
├── ServiceSpec 목록
├── ValidationSpec
└── DeliverySpec
```

첫 MVP에서는 ProjectSpec, ApplicationSpec, ModuleSpec, ModelSpec,
EndpointSpec까지만 구현한다. 나머지는 스키마 위치만 정의하거나 후속
버전으로 연기한다.

## ProjectSpec

프로젝트 전체의 식별 정보와 명세 참조를 정의한다.

```yaml
spec_version: "1"

project:
  name: Game Server
  package_name: game_server
  version: "0.1.0"
  description: 모듈형 FastAPI 게임 서버

application:
  framework: fastapi
  modules:
    - tutorial

generation:
  docker: false
  ci_provider: none
```

출력 경로는 ProjectSpec에 포함하지 않는다. 출력 위치는 CLI 또는
GenerationJob이 지정한다.

## ApplicationSpec

어떤 Module과 Service를 Application에 연결할지 정의한다.

```yaml
name: api
framework: fastapi
modules:
  - tutorial
services: []
```

향후 다음 항목을 확장할 수 있다.

- Middleware
- lifespan Hook
- CORS
- API Prefix
- Service 초기화 순서

첫 MVP에서는 복잡한 Middleware와 외부 Service를 포함하지 않는다.

## ModuleSpec

도메인 모듈 하나를 정의한다.

```yaml
spec_version: "1"

module:
  name: tutorial
  display_name: Tutorial
  route_prefix: /api/tutorial

models:
  - name: TutorialProgress
    fields:
      - name: current_step
        type: int
      - name: completed
        type: bool
        default: false

endpoints:
  - name: get_progress
    method: GET
    path: /progress
    response:
      model: TutorialProgress
    handler: get_progress

  - name: complete_step
    method: POST
    path: /complete
    request:
      fields:
        - name: step
          type: int
    response:
      model: TutorialProgress
    handler: complete_step
```

## Packet과 HTTP API의 관계

`common-tool`의 Packet과 Protocol 개념은 전송 방식과 분리해 일반화한다.

```text
MessageSpec
├── HTTP Endpoint
├── WebSocket Message
├── Queue Message
└── 내부 Event
```

첫 MVP는 HTTP Endpoint만 지원한다.

| C# 개념 | FastAPI 첫 구현 |
|---|---|
| Request Packet | Pydantic Request Schema |
| Response Packet | Pydantic Response Schema |
| Protocol Controller | FastAPI Router |
| Callback | Handler Method |
| Packet Model | Pydantic Model |
| Protocol ID | 선택적 Operation ID |

WebSocket Packet과 Queue Message는 동일 Type System을 재사용하는 후속
Generator로 확장한다.

## 공통 Type System

명세의 Type을 Python 구현과 직접 결합하지 않는다.

첫 MVP Type:

- string
- integer
- number
- boolean
- datetime
- uuid
- list
- optional
- 사용자 정의 Model 참조

예:

```yaml
- name: items
  type:
    list: ItemInfo

- name: nickname
  type:
    optional: string
```

Generator Plugin은 공통 Type을 Pydantic, SQLAlchemy, JSON Schema, DB Type
등으로 변환한다.

## 이름 검증

패키지와 Module 이름:

```regex
^[a-z][a-z0-9_]*$
```

추가로 다음을 거부한다.

- Python 예약어
- 경로 구분자와 `..`
- `__`로 시작하거나 끝나는 이름
- Windows 예약 파일 이름
- 대소문자만 다른 중복 이름

Class와 Model 이름:

```regex
^[A-Z][A-Za-z0-9]*$
```

Endpoint 이름과 Handler 이름:

```regex
^[a-z][a-z0-9_]*$
```

HTTP Path는 `/`로 시작해야 하며 `..`, 역슬래시, 빈 Segment를 허용하지
않는다.

## DatabaseSpec

후속 단계의 기본 형태는 다음과 같다.

```yaml
database:
  provider: sqlalchemy
  tables:
    - name: tutorial_progress
      fields:
        - name: user_id
          type: integer
          primary_key: true
        - name: current_step
          type: integer
          default: 0
```

첫 MVP에서는 Database 코드를 생성하지 않는다. 먼저 Type System,
Model, Router, Handler의 반복 생성을 검증한다.

향후 Database Plugin은 다음을 생성할 수 있다.

- SQLAlchemy Model
- Repository Protocol
- Repository 구현 골격
- Alembic Migration
- DB별 DDL
- Fake Repository

## Plugin Metadata와 명세 호환성

Plugin은 지원하는 명세 버전과 기능을 Metadata로 선언한다.

```yaml
plugin_id: autoforge.generator.fastapi
version: "1.0.0"
api_version: "1"
plugin_type: generator

capabilities:
  - project.generate
  - module.generate
  - endpoint.http.generate

supports:
  spec_versions:
    - "1"

permissions:
  workspace_write: true
  network: false
  subprocess: false
  git: false
```

Pipeline은 실행 전에 필요한 Capability와 Plugin 호환성을 확인한다.

## ValidationSpec

후속 명세 예:

```yaml
validation:
  steps:
    - import
    - pytest
    - ruff
    - package_build
```

각 단계는 Validator Plugin으로 확장할 수 있다. 한 단계라도 실패하면
Delivery 단계로 진행하지 않는다.

## DeliverySpec

Git과 CI/CD 자동화 단계에서 추가한다.

```yaml
delivery:
  provider: github
  branch_prefix: autoforge/
  create_pull_request: true

ci:
  provider: github_actions
  workflows:
    - test
    - build
```

Token, Password, Private Key 같은 비밀정보는 명세 파일에 저장하지 않는다.
실행 환경의 Secret Provider에서 주입한다.

## 명세 진화 원칙

- 모든 명세에 `spec_version`을 둔다.
- 알 수 없는 필드의 처리 정책을 명시한다.
- 호환되지 않는 변경은 새 명세 버전으로 올린다.
- Migration 없이 기존 명세를 조용히 재해석하지 않는다.
- Plugin은 지원 명세 버전을 Metadata로 선언한다.
- Manifest에 사용한 명세 버전과 Hash를 기록한다.
