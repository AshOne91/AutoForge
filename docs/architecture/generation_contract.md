# AutoForge 생성 계약

## 목적

이 문서는 AutoForge가 어떤 입력을 받아 어떤 파일을 생성하고, 반복 생성에서
사용자 코드를 어떻게 보호하며, 생성 결과를 어떻게 검증하는지 정의한다.

AutoForge는 일회성 프로젝트 Scaffold 도구가 아니다. 서버 개발에서 반복되는
Application 연결, API/Packet, Model, Router, Service, DB Schema, Repository,
Test, CI/CD 설정을 명세로 관리하는 생성 및 자동화 플랫폼이다.

## 생성 단위

### Project

새 저장소 또는 Python 패키지의 기본 구조를 생성한다.

- `src` 패키지 레이아웃
- `pyproject.toml`
- FastAPI Application Factory
- lifespan 기본 구조
- 설정과 로깅
- Health Router
- 테스트
- 선택적 Docker 및 CI/CD 설정

### Application

활성화된 Module과 Service를 조합한다.

- Router 등록
- Dependency Provider 등록
- Service 초기화 및 종료
- Module Metadata 등록
- Application 설정 조합

### Module

Account, Tutorial, Item처럼 하나의 도메인 기능 단위를 생성한다.

- Request/Response Schema
- Domain Model
- Router
- Handler 골격
- Service 골격
- Repository 계약
- 테스트

### Database

DB Schema 명세에서 저장 계층 코드를 생성한다.

- ORM Model
- Repository Protocol
- Persistence Adapter 골격
- Migration 또는 DDL
- 테스트용 Fake Repository

Database 생성의 Schema, Repository, Data Placement, Runtime Topology,
Transaction/Outbox 경계는 `database_generation.md`에서 정의한다.

### Durable Job

Durable Job은 외부 scheduler가 직접 업무 handler를 호출하지 않고,
token-protected /internal/jobs/{job_type} trigger/status API를 통해 Outbox와
worker로 전달되는 생성 계약이다. (job_type, run_key)는 idempotency key이며
동일한 요청은 같은 Job을 재사용한다.

`GET /internal/jobs/{job_type}?limit=1..100`은 해당 job type과 선언된 store에
한정된 최신 Job 이력을 반환한다. 정렬은 `updated_at` 내림차순, `job_id`
내림차순이며, 기존 trigger/status API와 같은 token 인증 경계를 사용한다.

Before the generated trigger opens a session or creates an outbox record, it
calls the scaffolded
`application.durable_job_handler.validate_durable_job_payload(job_type, payload)`
hook. The generated default accepts generic objects. A consumer validates only
its own job payloads; `TypeError` and `ValueError` become HTTP 422 responses.
The hook validates request input only: it does not execute work or change the
Durable Job idempotency and outbox contracts.

### Scoped service-token authentication

`ApplicationSpec.service_tokens` declares one named service caller and one
secret environment name per entry. A generated `EndpointSpec.service_token`
must name one of those callers; generation rejects an undeclared reference.
The generated `infrastructure/service_tokens.py` maps that name to its secret
environment and `require_service_token(name)` fails closed: an absent secret is
`503`, and a missing or mismatched Bearer token is `401`.

Durable Jobs use the logical `durable_jobs` caller. Existing Durable Job
projects retain `DURABLE_JOB_API_TOKEN` when they do not declare an override.
Generated Compose and Kubernetes application configuration receive the declared
secret environments; generated Airflow receives only the Durable Job token it
uses. A user-owned internal router may reuse the generated guard, but must use
its own declared caller name rather than sharing a Durable Job credential.

### User-owned runtime environments

`ApplicationSpec.runtime_environments` declares user-owned runtime environment
names without storing values. Each value has one or more explicit targets:
`application` is the compatibility default and `durable_job_worker` opts the
generated Durable Job worker into the value. Generated local Compose forwards a
required name as `${NAME:?set NAME}` and an optional name as `${NAME:-}` only to
its declared targets; the former fails before that process starts when absent,
while the latter is an empty value when absent. Generated
`environment/.env.example` lists each name with an empty value for the operator
to supply outside Git.

Generated Kubernetes application manifests reference only values targeted at
`application`; generated `secret.env.example` still lists every declared key.
The current Kubernetes topology does not yet generate a Durable Job worker
Deployment. Kubernetes therefore requires every injected application Secret key
to exist; `required: false` changes only local Compose fail-fast behavior and
does not make a missing injected Kubernetes Secret key valid. Specification
values and Secrets remain operator-owned and are never emitted into a manifest.

Generated `tests/test_health.py` sets application-targeted names from their
`health_test_value` before application lifespan starts. That value is test-only
and committed with the specification, so it MUST be non-secret; it is never
forwarded to Compose, Kubernetes, or a runtime Secret.

### Session access-level authorization

`EndpointSpec.access_level` selects a generated FastAPI session guard for a
human caller. It accepts `user`, `operator`, `developer`, or `administrator`
and requires the endpoint to declare `current_session`. The guard reads the
`access_level` value from the already-validated Redis `SessionData` claim and
uses that ordered hierarchy before the handler runs. A missing, malformed, or
insufficient claim returns `403`; it never falls back to a service token or an
implicit default.

Service tokens identify an internal service, not a human user or operator
role. `access_level` and `service_token` therefore cannot be combined on one
generated endpoint. The reusable `identity_session_profile` Blueprint generates
the global `LoginAccount.access_level` and `AccessLevelAudit` persistence
contract for fresh projects. Initial provisioning, the policy that writes an
audit record, and session revocation remain consumer-owned identity behavior.
An existing consumer adds an incremental migration rather than rewriting its
generated baseline; it must revoke existing user sessions when it changes a
persisted access level so stale Redis claims cannot retain prior authority.

DELETE /internal/jobs/{job_type}/{job_id}는 아직 worker가 claim하지 않은
requested Job만 cancelled로 전이한다. 이미 전달된 Outbox message는 삭제하지
않지만 worker의 원자적 requested → running claim이 실패하므로 handler를 실행하지
않는다. running, succeeded, failed Job은 취소할 수 없고, 취소는 완료된 외부
부수 효과를 되돌리지 않는다.

생성된 `durable-job-worker`와 `outbox-relay`의 컨테이너 재시작 정책은
`ApplicationSpec.durable_job_worker_restart_policy`에서 가져온다. 별도
relay별 정책 필드를 만들지 않으며, 기존 `aio-pika` 연결 확인을 Compose
healthcheck으로 표현한다. migration과 RabbitMQ의 초기 준비 상태는 생성된 Compose
`depends_on` 조건으로 검증한다.

생성된 application은 process liveness와 dependency readiness를 분리한다.
`/health`는 process liveness만 반환한다. `/readiness`는 생성된 모든 database
engine에 `SELECT 1`을 실행하고 SessionStore의 `health_check()`를 호출한다.
Redis SessionStore는 기존 client의 `PING`을 사용하며 Cluster mode에서는
`require_full_coverage=True` 설정도 유지한다. 하나라도 실패하면 `/readiness`는
`503`을 반환한다. Compose healthcheck와 Kubernetes application readiness probe는
이 endpoint를 사용하고, Kubernetes liveness probe는 계속 `/health`를 사용한다.

## 생성 파일 소유권

Python에는 C#의 `partial class`가 없으므로 파일 단위로 소유권을 분리한다.

### GENERATED

명세만으로 완전히 재현할 수 있는 파일이다.

```text
modules/item/generated/schemas.py
modules/item/generated/models.py
modules/item/generated/router.py
application/generated/module_registry.py
```

- AutoForge가 반복 생성할 수 있다.
- 사용자가 직접 수정하지 않는다.
- Generator와 명세 Hash를 Metadata에 기록한다.
- 내용 Hash가 예상과 다르면 수동 변경으로 판단하고 정책에 따라 충돌시킨다.

When `tooling.distributed_lock.enabled`, `tooling.external_provider.enabled`,
`tooling.key_value_store.enabled`, `tooling.search.enabled`,
`tooling.vector_store.enabled`, or `tooling.storage.runtime_enabled` is selected,
every file under the corresponding `infrastructure/distributed_lock/`,
`infrastructure/external_provider/`, `infrastructure/key_value_store/`,
`infrastructure/search/`, `infrastructure/vector_store/`, or
`infrastructure/object_storage/` path is GENERATED. Each contains configuration,
transport protocol, deterministic fake, provider adapter, and explicit service
lifecycle boundary. The consumer owns FastAPI lifespan registration, lock-key and
critical-section policy, cache key/value/invalidation policy, provider credentials
and schemas, index or collection schema, object key layout, document projection,
embedding, and query/relevance policy. Regeneration must not turn generated
services into process-global singletons or overwrite consumer code.

### SCAFFOLDED

최초 한 번만 골격을 생성하고 이후 사용자 소유로 전환되는 파일이다.

```text
modules/item/handlers.py
modules/item/service.py
application/extensions.py
application/message_topology.py
```

- 파일이 없을 때만 생성한다.
- 파일이 있으면 변경하지 않는다.
- 명세에 새 Handler가 추가돼도 기존 파일을 자동 덮어쓰지 않는다.
- 누락된 구현은 검증 결과 또는 별도 보조 파일로 보고한다.

`application/extensions.py` is scaffolded application composition: generated
`app_factory.py` includes its `USER_ROUTERS`, while AutoForge preserves later
consumer edits. Application-specific internal endpoints register here instead of
patching a generated router.

The same scaffold may declare ordered `USER_LIFESPANS` FastAPI lifespan
factories. The generated application always owns the outer lifespan: generated
database, session, and heartbeat contexts enter first; user contexts enter next
and therefore exit first through `AsyncExitStack`. A preserved older extension
without `USER_LIFESPANS` is treated as an empty tuple, so regeneration does not
require a consumer-owned compatibility edit. This is application composition,
not a `ModuleSpec` lifecycle field or a global service container.

When RabbitMQ is selected, `application/message_topology.py` is also scaffolded.
The generated Outbox relay invokes `declare_user_message_topology(connection)`
after its publisher starts and before it scans Outbox records. The default hook
is a no-op; a consumer declares only its domain queue bindings there, without
patching the generated relay or placing message handling business logic in it.

### USER_OWNED

사용자가 직접 만든 파일이다.

```text
modules/item/custom/pricing.py
modules/item/custom/reward_policy.py
```

AutoForge는 생성, 변경, 삭제하지 않는다.

## 권장 Python 출력 구조

```text
src/<package_name>/
├── application/
│   ├── app_factory.py
│   ├── lifespan.py
│   └── generated/
│       └── module_registry.py
├── modules/
│   └── <module_name>/
│       ├── generated/
│       │   ├── schemas.py
│       │   ├── models.py
│       │   ├── router.py
│       │   └── metadata.json
│       ├── handlers.py
│       ├── service.py
│       └── custom/
├── services/
├── infrastructure/
└── main.py
```

`generated` 디렉터리는 기계 생성 영역이고, 그 밖의 Handler 및 Custom
디렉터리는 사용자 코드 영역이다.

## 생성 계획

Generator는 파일을 쓰기 전에 GenerationPlan을 만든다.

각 계획 항목은 다음 정보를 가진다.

- 상대 경로
- Generator ID와 버전
- 소유권
- 예정 작업
- 명세 Hash
- 예상 내용 Hash
- 교체 대상의 이전 Content Hash
- 의존 명세 또는 Module

예정 작업은 다음 중 하나다.

- CREATE
- REPLACE_GENERATED
- KEEP
- SKIP
- CONFLICT

Dry-run은 GenerationPlan만 반환하고 파일시스템을 변경하지 않는다.

## Manifest

GenerationManifest는 실제 실행 결과를 기록한다.

- 작업 ID
- ProjectSpec 버전과 Hash
- 생성 파일 목록
- 파일별 소유권
- Generator ID와 버전
- 명세 Hash와 내용 Hash
- 생성, 변경, 동일, 건너뜀, 충돌, 실패 상태

Manifest 경로는 Workspace를 기준으로 한 상대 경로만 사용한다.
GenerationJobManifest는 여러 GenerationUnit의 Manifest를 Job 단위로 묶고
Job ID, Unit ID, 명세 버전·Hash와 전체 상대 경로의 중복을 검증한다.

## 반복 생성 규칙

1. ProjectSpec과 ModuleSpec을 검증한다.
2. 현재 Manifest와 파일 Hash를 읽는다.
3. GenerationPlan을 만든다.
4. USER_OWNED 파일은 대상에서 제외한다.
5. SCAFFOLDED 파일이 이미 있으면 보존한다.
6. GENERATED 파일에 예상하지 못한 수동 변경이 있으면 충돌로 처리한다.
7. 임시 Workspace에서 새 결과를 생성한다.
8. Import, Test, Build 검증을 실행한다.
9. 검증 성공 후에만 대상에 적용한다.
10. 새 Manifest를 기록한다.

강제 덮어쓰기 옵션은 기본값이 아니며 별도 승인과 명시적 옵션이 필요하다.

`REPLACE_GENERATED`는 이전 Manifest가 같은 Generator와 source로 기록한
GENERATED 파일에만 허용한다. 현재 파일 Hash가 Manifest Content Hash와
일치해야 하며, 적용 직전에도 같은 이전 Hash를 다시 확인한다.

## 생성 과정의 Event

Generator와 Pipeline은 다음 수명주기 Event를 발행한다.

- `GenerationJobPlannedEvent`
- `GenerationStartedEvent`
- `GenerationCompletedEvent`
- `GenerationFailedEvent`
- 검증 시작·완료·실패 Event
- Git Commit·Push·Pull Request Event

Event는 상태 알림과 Logging, Audit, Metrics뿐 아니라 AutoForge 주요
컴포넌트 사이의 통신 경계에도 사용한다. EventBus는 업무 로직이나 실행
순서를 제어하지 않는다. Pipeline이 Task 순서와 실패 정책을 소유하고
Application Handler가 처리 결과를 Event로 발행한다. 상세 경계는
`event_driven_architecture.md`를 따른다.

## 검증 조건

생성 성공은 파일 쓰기 성공만 의미하지 않는다.

1. 명세 검증 성공
2. Workspace 경로 검증 성공
3. 충돌 정책 통과
4. 계획된 파일 생성 성공
5. Python Import 성공
6. 생성 프로젝트 pytest 성공
7. 선택된 Validator Plugin 성공
8. Manifest 기록 성공

검증 실패 시 Git Commit, Push, Pull Request를 실행하지 않는다.
