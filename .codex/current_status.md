# 현재 상태

## 2026-08-03 인증된 GenerationJob 제출 API 완료

- `GenerationJobSubmission`이 source/output root 기준 상대경로를 Job snapshot에 저장해
  다른 worker가 재시작 후에도 실행 입력을 복원할 수 있게 했다.
- Application service가 명세를 먼저 검증하고 Job unit hash를 만든 뒤 idempotency key로
  원자적 claim한다. 같은 key의 경로 또는 명세가 달라지면 충돌로 거부한다.
- FastAPI adapter는 Bearer token, 1~255자 `Idempotency-Key`, 4 KiB 기본 streaming
  body 제한과 root 이탈 방지를 적용한다.
- POST는 신규 Job에 202, 동일 요청 재전달에 200, key 재사용 충돌에 409를 반환하고,
  GET은 저장된 Job 상태를 조회한다.
- 서로 다른 FastAPI 앱 2개가 실제 PostgreSQL 16에 동시에 같은 요청을 제출해도
  202 응답과 Job row가 하나만 생성되는 것을 검증했다.
- HTTP 요청 안에서는 생성 Pipeline을 실행하지 않는다. 다음 단계는 lease 기반 worker
  claim, heartbeat와 abandoned Job 복구다.

## 2026-08-03 PostgreSQL Control Plane 기반 완료

- SQLAlchemy/asyncpg를 로컬 CLI 필수가 아닌 `server` optional extra로 분리했다.
- PostgreSQLJobStore가 JSONB Job snapshot, unique idempotency key, status CAS와
  revision 증가를 구현한다.
- PostgreSQLAuditSink가 envelope-only audit를 event_id 기준으로 중복 없이 append한다.
- schema는 runtime create_all이 아니라 버전 관리되는
  `deploy/postgresql/init/001_control_plane.sql`이 소유한다.
- 실제 PostgreSQL 16에서 동시 claim 2건 중 생성 1건, status 전이 경쟁 중 성공 1건,
  동일 audit append 2건 중 row 1건을 검증했다.
- Compose credential은 로컬 통합 테스트 전용이며 운영 secret 계약은 후속 배포
  단계에서 별도로 구현한다.
- 후속 단계에서 인증된 idempotent trigger/status API를 구현했다. 다음은 실행
  lease와 worker 복구다.

## 2026-08-03 Observability Handler 기반 완료

- Event 구독에 `critical`과 `observational` 실패 정책을 명시한다.
- 기본값은 기존 의미를 보존하는 critical이며, 동일 Event의 모든 handler를 실행한
  뒤 critical 실패를 구조화된 `EventDispatchError`로 전파한다.
- observational 실패는 핵심 Pipeline을 실패시키지 않고 `EventDispatchResult`에
  handler type, 정책과 원인 예외를 기록한다.
- 구조화된 Logging Handler와 Audit Handler는 임의 payload를 복사하지 않고 Event
  envelope만 기록하여 비밀정보 노출 경계를 지킨다.
- async AuditSink Protocol과 append-only InMemoryAuditSink를 추가했다.
- InMemoryAuditSink는 로컬·테스트 adapter이며 재시작 복구, 분산 중복 방지와 규정
  보존을 제공하지 않는다. 분산 실행용 PostgreSQL adapter는 후속 단계에서 구현했다.
- 전체 Ruff, 312개 pytest와 CLI 버전 검증을 통과했다.

## 2026-08-03 Event/Pipeline Core 완료

- 기존 in-process EventBus의 업무 중립성을 유지하면서 Event를 불변 객체로 만들고
  timezone-aware UTC, schema version, correlation/causation, job과 producer metadata를
  추가했다.
- 기존 subscribe/unsubscribe/handlers/publish API를 유지하고, 외부에서 내부 구독
  목록을 변경할 수 없도록 snapshot을 반환한다.
- SequentialPipeline이 명시적인 Task 순서, task별 timeout, 제한된 retry, 실패 중단과
  cancellation을 조정한다.
- Pipeline/Task의 started/completed/failed/retry/cancelled event를 발행하며 EventBus는
  Task나 Pipeline의 실행 규칙을 알지 않는다.
- Core Event/Pipeline 집중 테스트 8개, Job lifecycle 집중 테스트 7개와 전체
  295개 테스트, Ruff를 통과했다.
- 다음 단계는 기존 GenerationJob 상태 모델과 실제 생성·검증 서비스를 이 Pipeline에
  연결하는 Application 수직 슬라이스다.

## 2026-08-03 GenerationJob lifecycle 기반 완료

- Job/Generation/Validation의 created/started/completed/failed Event 계약을 추가했다.
- GenerationJob 상태 전이를 pending → generating → validating → succeeded 순서로
  제한하고, 어느 실행 단계에서든 명시적 failed 전이를 지원한다.
- 상태 전이는 기존 객체를 변경하지 않고 새 snapshot을 만들며 Pydantic 전체
  불변조건을 다시 검증한다.
- async JobStore Protocol과 테스트·로컬 CLI용 InMemoryJobStore adapter를 추가했다.
- replace 시 expected status를 비교해 같은 Job의 동시 실행이 조용히 상태를
  덮어쓰지 못하게 한다.
- InMemory adapter 자체는 영속 Job Store가 아니다. 분산 실행용 PostgreSQL adapter와
  idempotent claim은 후속 단계에서 구현했다.

## 2026-08-03 Generation Application Pipeline 완료

- 기존 generate CLI 안의 명세 로딩, 교차 참조 검증, 생성과 manifest 저장 업무를
  `application/generation`으로 이동했다.
- 실제 실행 순서는 prepare_generation_job → generate_units →
  validate_generated_project 세 Task로 명시했다.
- JobStore에 상태를 먼저 저장한 뒤 Job/Generation/Validation Event를 발행한다.
- 생성 결과의 import, pytest, Ruff와 wheel build가 모두 성공해야 GenerationJob을
  succeeded로 전이한다. 검증 실패는 failed 상태와 실패 Event를 남긴다.
- CLI는 Application Pipeline을 조립하고 사용자 입력 오류와 실행 오류를 표시하는
  얇은 adapter가 됐다. 기존 검증 helper 공개 경계는 호환 wrapper로 보존했다.
- 실제 검증을 연결하면서 발견한 endpoint 없는 Router의 unused handlers import와
  import 구역 공백 생성 오류를 수정했다.
- 전체 Ruff, 299개 pytest와 `python -m autoforge.main version`을 통과했다.
- 후속 단계에서 logging/audit handler, PostgreSQL JobStore와 idempotent claim을
  구현했다.
- KIS 실사용 검증 중 GENERATED `pyproject.toml`의 프로젝트별 품질 도구 설정이
  명세에 없음을 확인해 `ToolingSpec.ruff_exclude` 계약을 추가했다.
- exclude 항목은 안전한 Workspace 상대 POSIX 경로만 허용하며 FastAPI Project
  Generator가 결정적인 `[tool.ruff]` 설정으로 렌더링한다.
- 전체 테스트 기준선은 312개다.
- wheel 검증이 만드는 `build/`, `dist/`와 `.autoforge/dist/`를 포함한 기본
  `.gitignore`를 Project Generator의 SCAFFOLDED 파일로 추가했다. 기존 프로젝트의
  사용자 `.gitignore`는 덮어쓰지 않는다.

## 2026-08-03 RabbitMQ/Transactional Outbox 완료

- Project `ServiceSpec`에 RabbitMQ connection, exchange, queue, routing key,
  dead-letter와 outbox store 계약을 추가했다.
- Messaging Generator가 aio-pika publisher/consumer, Outbox writer/relay,
  Processed Message Inbox, store별 immutable Alembic revision과 실행 script를 생성한다.
- Publisher confirm, persistent message, mandatory routing, durable topology,
  manual ACK, DLX/DLQ와 transport 오류만 재시도하는 경계를 적용했다.
- KIS Profile 저장과 Outbox event 기록이 선택된 account shard의 같은 transaction에서
  수행되는 것을 단위 테스트와 실제 PostgreSQL로 검증했다.
- RabbitMQ 중단 중 API 저장과 pending Outbox 기록, 재시작 후 발행/소비,
  동일 event 재발행 시 Inbox row 1개 유지, volume 기반 durable queue 복구를 검증했다.
- 다음 단계는 기존 generic EventBus를 업무 로직 없이 유지하면서 Job Event와
  Pipeline 실행 조정 계층을 구현하는 것이다.

## 완료

- 설정 로딩 기본 구조
- Registry 안정화
- Plugin 기반 클래스와 Metadata
- PluginManager 안정화
- 기존 Generator를 보존하는 Generator Plugin Adapter
- Plugin ID·버전·Capability·지원 Specification 버전 정합성 검증
- Plugin API v1 호환성 검증
- 버전형 Plugin 의존성과 외부 자원 접근 권한 정책
- Plugin 디렉터리 자동 발견과 plugin.json 검증
- 발견 과정의 Symlink 이탈·중복 ID·손상 Manifest 거부
- Plugin 코드를 실행하지 않는 Metadata 발견 단계
- Plugin 누락·버전 불일치·순환 의존성 검증
- 의존성이 먼저 오는 결정적 Plugin 로드 순서
- 명시적 trusted Entrypoint Import와 Factory 계약 검증
- PluginManager 의존성 순서 등록과 실패 Rollback
- Specification 타입별 Generator Plugin Registry
- FastAPI Project/Module Generator의 실제 Plugin 등록
- 요청·결과 타입별 async Validator Plugin Registry
- ProjectValidator의 실제 Plugin 등록과 권한 선언
- Built-in Generator/Validator Plugin Catalog와 명시적 의존성 주입
- 코드·아키텍처·FastAPI 학습 가이드 작성
- Python·웹·FastAPI·AutoForge 4권 완전 입문 학습 시리즈 작성
- Event와 비동기 EventBus 기본 구조
- EventBus 중심 장기 통신 아키텍처와 Pipeline 책임 경계 확정
- Task와 TaskManager 기본 구조
- 기존 테스트의 pytest 마이그레이션
- ProjectSpec과 ModuleSpec 검증 모델
- 첫 MVP 공통 Type System
- GenerationPlan과 GenerationManifest 모델
- 명세와 파일 내용 Hash 계산
- Workspace 상대경로 검증과 경로 이탈 방지
- 작업별 격리 Workspace 생성과 자동 정리
- 실패 진단용 격리 Workspace 명시적 보존 정책
- 제네릭 Generator Protocol
- 최소 FastAPI Project Generator 렌더링과 Dry-run
- Workspace 상태 기반 생성 계획 충돌 판정
- GenerationPlan의 안전한 Workspace 적용과 메모리 Manifest 생성
- GenerationManifest의 결정적 JSON 저장과 검증된 로딩
- 비동기 외부 프로세스 실행과 Timeout 처리
- 생성 프로젝트 Import 및 pytest 검증
- 생성 프로젝트 Ruff 및 wheel Package Build 검증
- 공통 Type의 Python/Pydantic Type 변환
- 기술 중립 DatabaseSpec, Table/Column과 DataPlacement 최소 계약
- Repository 명세와 Module Aggregate/Table 참조 무결성 검증
- kis-auto-trading Account/Profile 실제 명세 검증
- Repository Protocol과 Fake Repository Generator
- Repository Generator의 Module Plugin Catalog 등록
- PostgreSQL Global/Shard DDL Generator의 Module Plugin Catalog 등록
- kis-auto-trading 로그인(Global)과 개인정보(Shard) 명세 및 재현 SQL 검증
- SQLAlchemy async Base, Session Registry와 ShardRouter Generator
- ModuleSpec 기반 SQLAlchemy 2.x Record Model Generator
- AsyncSession 주입형 SQLAlchemy Repository Adapter와 Domain/Record 변환 Generator
- kis-auto-trading Identity/Account 실제 명세 SQLAlchemy 렌더링 검증
- kis-auto-trading UserProfileRepository 실제 렌더링 검증
- ModuleSpec 기반 Pydantic Model 및 Request/Response Schema 생성
- ModuleSpec 기반 FastAPI Router와 Handler Scaffold 생성
- 동일 명세 재실행 시 사용자 Handler 보존
- Manifest 기반 GENERATED 파일 안전 교체
- Endpoint 추가 재생성 시 Router 갱신과 Handler 보존
- Application Module Registry 생성
- Project와 Tutorial Module 조합 및 실제 Endpoint 검증
- GenerationJob과 Project/Module Unit 집계 모델
- 복수 Manifest의 Job ID, Specification과 파일 경로 중복 검증
- 버전형 GenerationJobManifest의 결정적 JSON 저장과 검증된 로딩
- 기존 GenerationManifest JSON 로딩 호환성
- 명시적 Config 주입과 전역 Config 제거
- 프로젝트 디렉터리 밖에서 동작하는 version CLI
- 미구현 CLI의 명확한 실패 상태
- 전체 테스트 295개 통과 기준선

## 진행 중

- Store별 Alembic 실행 환경과 immutable baseline revision 생성을 완료했다.
- kis-auto-trading의 identity DB와 account DB 2개에 migration 적용을 검증했다.
- Bearer current_session 의존성 생성을 추가했다.
- kis-auto-trading Account/Profile을 실제 선택된 shard DB에 저장하고 API 2대 교차
  조회 및 반대 shard 미저장을 검증했다.
- Redis Cluster async provider와 사용자 단위 hash-tag 세션 키 계약을 생성한다.
- kis-auto-trading에서 3 Primary + 3 Replica, 전체 16,384 slot coverage, 담당
  Primary 중지와 Replica 승격, 기존 읽기·신규 쓰기 및 volume 재기동을 검증했다.
- RabbitMQ Transport와 Transactional Outbox를 완료했다.
- generic Event/Pipeline Core, GenerationJob lifecycle과 실제 생성·검증 Application
  연결을 완료했다.
- 문서 정합성 정리
- 패키지와 코딩 스타일 정리
- Plugin Framework 4단계 완료 검토

## 존재하지만 미완성

- 일부 CLI 명령
- Plugin Permission의 OS 수준 Sandbox 강제
- 실행 lease, heartbeat와 abandoned Job 복구

PluginLoader의 발견, 의존성 정렬과 명시적 trusted 로딩 및 GenerationJob Application
Pipeline 연결은 완료됐다. 다만 Webhook부터 Git 반영까지 이어지는 자동화 제품 전체는
아직 완성되지 않았다.

## 시작하지 않음

- Build 및 Git 서비스
- Webhook 서비스
- AI 생성

## 현재 제약

로컬 생성과 검증이 안정되기 전에 Webhook, Git 자동화, AI를 구현하지 않는다.
Plugin 발견과 실행은 분리한다. 신뢰 여부가 확인되지 않은 Plugin에는
`load_trusted()`를 호출하지 않는다.

미래 단계용 빈 디렉터리는 미리 유지하지 않는다. 각 단계에 진입할 때
Roadmap과 다음 작업 문서를 확인하고 필요한 패키지와 테스트 디렉터리를
구현과 함께 생성한다.

전체 인수인계 문서는 `docs/PROJECT_GUIDE_2026-07-29.md`를 참고한다.
