# AutoForge 명세 설계

## 명세 계층

AutoForge 명세는 하나의 거대한 파일에 모든 내용을 넣지 않는다.

```text
ProjectSpec
├── ProjectInfo
├── ApplicationSpec
│   ├── Module 참조
│   ├── ServiceSpec 목록
│   ├── DatabaseStoreSpec 목록
│   └── DurableJobSpec 목록
└── ToolingSpec

ModuleSpec
├── ModuleInfo
├── ModelSpec 목록
├── EndpointSpec 목록
└── 선택적 DatabaseSpec
```

ProjectSpec은 프로젝트 조립과 도구 설정을 소유하고, 별도 ModuleSpec은 각
도메인의 HTTP·Model·Database 계약을 소유한다.

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

tooling:
  docker:
    enabled: false
```

### ToolingSpec

생성 프로젝트의 재현 가능한 개발·실행 환경 설정을 선언한다. ToolingSpec은
Ruff 제외 경로와 CI, Docker, ELK, RAG, Storage, Kubernetes,
Local Environment 명세를 포함한다.

```yaml
tooling:
  ruff_exclude:
    - base_server
    - test.py
```

Workspace 상대 POSIX 경로만 허용한다. 절대경로, 드라이브 경로, `..`, 역슬래시와
중복 경로는 거부한다. `pyproject.toml`은 GENERATED 파일이므로 직접 수정하지 않고
이 명세를 변경한 뒤 재생성한다.

출력 경로는 ProjectSpec에 포함하지 않는다. 출력 위치는 CLI 또는
GenerationJob이 지정한다.

### RAG local search backend

`tooling.rag.search_backend` selects exactly one local keyword-and-vector search
service: `elasticsearch` (the default) or `opensearch`. The generated environment
uses `RAG_SEARCH_BACKEND` and `RAG_SEARCH_URL`, so application and worker code do
not depend on a provider-specific service name. Elasticsearch uses its
`dense_vector` mapping; OpenSearch uses its `knn_vector` mapping.

This contract covers generated local containers only. Managed cloud search
services, including AWS OpenSearch Service authentication, are not generated or
runtime-verified by this setting.

### Local database provider

`tooling.local_environment.database_provider` selects the local generated
database runtime: `postgresql` (default) or `mysql`. `postgres_mode: ha` is a
PostgreSQL-only setting. `mysql_mode` defaults to `standalone`; its `ha` value
is valid only when `database_provider: mysql`, and MySQL rejects a non-standalone
`postgres_mode`. MySQL HA generates a three-member InnoDB Cluster and a
version-matched Router writer endpoint. The local MySQL profile rejects
PostgreSQL-specific RabbitMQ, Outbox, and Durable Job generation.
Database-generation details are owned by
[`database_generation.md`](database_generation.md).

### Kubernetes MySQL Operator profile

`tooling.kubernetes.mysql_operator` is a separate opt-in profile for the
selected MySQL Operator for Kubernetes provider. When enabled, it requires a
bootstrap Secret reference, TLS Secret reference, cluster name, explicit MySQL
version, member and Router replica counts, StorageClass, and PVC size. The
profile requires the Kubernetes base-server profile and rejects reuse of its
application runtime Secret as the Operator bootstrap Secret. It declares
deployment input and causes the Kubernetes generator to render an
`InnoDBCluster` manifest.

### Local RabbitMQ mode

`tooling.local_environment.rabbitmq_mode` is `standalone` by default. The
opt-in `cluster` value is valid only with `local_environment.enabled: true` and
the application's single RabbitMQ `ServiceSpec` set to `queue_type: quorum`.
`queue_type` defaults to `classic`; a quorum type may still describe an
externally managed broker when the local environment is disabled.

Cluster mode changes only the generated local broker topology. It preserves the
consumer-facing `RABBITMQ_URL` contract and does not select a cloud broker,
database shard, or Airflow topology.

### Local Airflow scheduler replicas

`tooling.local_environment.airflow_scheduler_replicas` defaults to `1`. The
default local Durable Job profile generates one `airflow-scheduler` with
`SequentialExecutor`. A value of `2` or more is opt-in single-host scheduler
HA and requires `local_environment.enabled: true`, at least one Durable Job,
and `postgres_mode: ha`.

The HA profile generates indexed scheduler services, uses `LocalExecutor`,
the PostgreSQL HA writer endpoint, a shared user-owned `AIRFLOW_FERNET_KEY`,
and independent scheduler health checks. It changes scheduler-process
multiplicity only: webserver replicas, triggerer replicas, remote executors,
and multi-host deployment are not selected by this field.

## ApplicationSpec

어떤 Module과 Service를 Application에 연결할지 정의한다.

```yaml
name: api
framework: fastapi
modules:
  - tutorial
services: []
databases: []
durable_jobs: []
```

ApplicationSpec은 FastAPI Framework, Module 참조, Redis/RabbitMQ Service,
Runtime Database Store와 Outbox 기반 Durable Job을 선언한다. 이름과 참조의
중복·누락은 명세 검증 단계에서 거부한다.

`durable_job_worker_restart_policy`는 Durable Job worker 컨테이너의 재시작
정책을 명시한다. 기본값은 `unless-stopped`이며, 이 필드는 현재 단일
`durable-job-worker` 구성의 생명주기 경계만 소유한다. worker의 이벤트·큐
계약은 각 `DurableJobSpec`과 RabbitMQ `ServiceSpec`이 소유하고, 의존 서비스
준비 상태는 생성된 Compose `depends_on` health 조건으로 표현하고, worker
worker와 relay의 RabbitMQ 연결 가능 여부는 기존 `aio-pika`를 사용하는
생성된 Compose healthcheck으로 표현한다.
application liveness와 readiness의 상세 생성 계약은
[Generation Contract](generation_contract.md)가 소유한다. Compose와 Kubernetes는
각각 생성된 `/readiness`와 `/health` probe를 재사용하며, 이 명세 문서는 별도
healthcheck 구현을 다시 정의하지 않는다.

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

## HTTP API 계약

ModuleSpec의 EndpointSpec은 Pydantic Request/Response Schema, FastAPI Router와
Handler 연결을 정의한다. HTTP 이외의 Transport Message는 이 명세 버전의
계약에 포함하지 않는다.

## Module 책임 경계

```text
Module Specification
  ├─ Domain Model
  ├─ HTTP API 계약
  ├─ Persistence 계약
  └─ 생성 파일 소유권

Application Composition
  └─ 선택한 Module, Transport와 Adapter를 연결
```

FastAPI Router는 입출력과 Transport 변환만 담당하고 업무 규칙은 Handler 또는
Application Service가 담당한다. EventBus도 Module 업무를 직접 실행하지 않는다.

## 공통 Type System

명세의 Type을 Python 구현과 직접 결합하지 않는다.

지원 Type:

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

기본 형태는 다음과 같다.

```yaml
database:
  provider: agnostic
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

Database 명세로 다음 생성물을 만든다.

- SQLAlchemy Model
- Repository Protocol
- Repository 구현 골격
- PostgreSQL DDL
- Fake Repository

Database 관련 정보는 다음 책임으로 분리한다.

- Schema Specification: 테이블, 필드, 키, 인덱스, 관계
- Repository Specification: Application이 요구하는 저장 동작
- Data Placement Specification: Global 또는 Shard 배치와 partition key
- Runtime Database Configuration: 환경별 DSN Secret 참조와 연결 풀

Schema 명세에는 host, password 같은 운영 접속 정보를 넣지 않는다. Shard
라우팅이 실패하면 Global DB로 자동 대체하지 않으며, 명시적인 오류 정책을
사용한다.

상세 경계는 `database_generation.md`를 따른다. Repository와 Transaction은
다음 원칙을 지킨다.

- Transaction은 Repository가 아니라 request/job Unit of Work가 소유한다.
- Global과 Shard 작업을 암묵적으로 한 Transaction처럼 취급하지 않는다.
- Shard routing 실패 시 Global로 대체하지 않는다.
- 물리 Shard 수와 DSN은 운영 설정이며 업무 명세에 Secret으로 기록하지 않는다.

## Plugin Metadata와 명세 호환성

Plugin은 지원 명세 버전과 Capability를 Metadata로 선언하고 Pipeline은 실행
전에 호환성을 확인한다. Metadata 필드와 권한 계약은 `plugin_system.md`가
소유한다. Token, Password, Private Key 같은 비밀정보는 명세에 저장하지 않고
실행 환경의 Secret Provider에서 주입한다.

## 명세 진화 원칙

- 모든 명세에 `spec_version`을 둔다.
- 알 수 없는 필드의 처리 정책을 명시한다.
- 호환되지 않는 변경은 새 명세 버전으로 올린다.
- Migration 없이 기존 명세를 조용히 재해석하지 않는다.
- Plugin은 지원 명세 버전을 Metadata로 선언한다.
- Manifest에 사용한 명세 버전과 Hash를 기록한다.
