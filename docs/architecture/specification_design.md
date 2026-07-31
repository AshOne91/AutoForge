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

현재 ProjectSpec, ApplicationSpec, ModuleSpec, ModelSpec, EndpointSpec과
DatabaseSpec의 첫 수직 단면까지 구현되어 있다. ServiceSpec, ValidationSpec과
DeliverySpec은 아직 명세 모델로 구현하지 않았다.

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

현재 구현은 `framework`와 Module 목록만 지원한다. game-server 분석 결과,
Application은 장기적으로 API, Worker, Scheduler 같은 실행 역할, 역할별 Module,
Service와 Adapter, lifespan 초기화와 역순 종료를 조립하는 Composition Root여야
한다. 이 요구를 현재 명세 버전에 즉시 추가하지 않고 실제 수직 흐름에서 필요한
최소 계약부터 검증한다.

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

Protocol ID는 배포된 생산자와 소비자가 같은 동작을 식별하기 위한 안정적인
계약이다. HTTP operation ID, WebSocket message type, Queue routing key와 내부
Event type은 서로 다른 전송 방식에서도 동일한 업무 동작에서 파생될 수 있다.
현재는 HTTP만 생성하며 MessageSpec은 아직 구현하지 않는다.

## Module과 Template의 관계

game-server의 Template은 렌더링 파일이 아니라 Account, Item, Shop 같은 업무
모듈이다. AutoForge의 Module은 이 책임을 계승하되 정적 Context와 callback을
그대로 옮기지 않는다.

```text
Module Specification
  ├─ Domain Model
  ├─ API/Message 계약
  ├─ Persistence 계약
  ├─ Service 의존성(후속)
  └─ Lifecycle 요구(후속)

Application Composition
  └─ 선택한 Module, Transport와 Adapter를 연결
```

FastAPI Router는 입출력과 Transport 변환만 담당하고 업무 규칙은 Handler 또는
Application Service가 담당한다. EventBus도 Module 업무를 직접 실행하지 않는다.

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

현재 PostgreSQL Global/Shard DDL, 기술 중립 Repository/Fake, SQLAlchemy async
기반 구조, ORM Record와 Repository Adapter까지 생성한다. Alembic 실행 환경과
실제 DB 접속 통합은 아직 구현하지 않았다.

향후 Database Plugin은 다음을 생성할 수 있다.

- SQLAlchemy Model
- Repository Protocol
- Repository 구현 골격
- Alembic Migration
- DB별 DDL
- Fake Repository

Database 관련 정보는 다음 책임으로 분리한다.

- Schema Specification: 테이블, 필드, 키, 인덱스, 관계
- Repository Specification: Application이 요구하는 저장 동작
- Data Placement Specification: Global 또는 Shard 배치와 partition key
- Runtime Database Configuration: 환경별 DSN Secret 참조와 연결 풀

Schema 명세에는 host, password 같은 운영 접속 정보를 넣지 않는다. Shard
라우팅이 실패하면 Global DB로 자동 대체하지 않으며, 명시적인 오류 정책을
사용한다.

상세 경계와 첫 실제 검증 대상은 `database_generation.md`를 따른다.

game-server의 UserDB/DBLoad/DBSave는 한 Table CRUD보다 넓은 사용자 Aggregate
로드와 저장을 수행한다. 현재 Repository의 `find_by_id`와 `save`는 의도적으로
작은 첫 계약이다. Aggregate 조립, Unit of Work와 변경 추적은 다음 원칙으로
확장한다.

- 실제 서비스 흐름에서 필요한 경우에만 계약을 추가한다.
- Transaction은 Repository가 아니라 request/job Unit of Work가 소유한다.
- Global과 Shard 작업을 암묵적으로 한 Transaction처럼 취급하지 않는다.
- Shard routing 실패 시 Global로 대체하지 않는다.
- 물리 Shard 수와 DSN은 운영 설정이며 업무 명세에 Secret으로 기록하지 않는다.

## 현재 계약과 장기 확장 후보

| 영역 | 현재 구현 | 장기 후보 |
|---|---|---|
| Application | FastAPI, Module 목록 | 실행 역할, Service/Module composition |
| Interface | HTTP Endpoint | WebSocket, Queue Message, Event |
| Persistence | Table, Repository, Placement | Aggregate load/save, 관계, UoW 정책 |
| Runtime DB | async Session, ShardRouter | replica/read policy, topology reference |
| External Service | 미구현 | Redis/RabbitMQ capability와 wiring |
| Delivery | 미구현 | Docker, Kubernetes, CI/CD, Git |

장기 후보는 구현 완료를 의미하지 않으며 현재 명세가 수용해야 할 방향만 기록한다.

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
