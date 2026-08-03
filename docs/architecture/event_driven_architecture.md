# AutoForge Event-Driven Architecture

- 상태: 장기 아키텍처 결정
- 확정일: 2026-07-30
- 구현 상태: in-process EventBus와 generic sequential Pipeline Core 구현됨

## 1. 목적

AutoForge는 주요 컴포넌트가 구체적인 구현을 직접 참조하는 대신 Event를 통해
통신하는 event-driven 시스템을 지향한다.

```text
GitHub Push
  → Webhook
  → EventBus
  → Pipeline
  → Task
  → Plugin
  → Generator
  → Git
  → Notification
```

이 흐름은 EventBus가 모든 업무를 직접 실행한다는 뜻이 아니다.

```text
EventBus = 중앙 통신 메커니즘
Pipeline = Job 내부 실행 순서와 실패 정책
Handler  = Event와 Application 동작의 연결부
Service  = 실제 유스케이스
Task     = Pipeline의 최소 작업 단위
Plugin   = 교체하거나 확장할 수 있는 기능
```

## 2. 확정 원칙

### EventBus는 중앙 통신 수단이다

Webhook, Pipeline, Task, Plugin, Generator, Git과 Notification에서 발생한
주요 상태 변화는 Event로 표현하고 EventBus로 전달한다. Producer는 구체적인
Consumer를 알지 않는다.

```text
Webhook
  └─ RepositoryPushed Event 발행

PipelineRequestedHandler
  └─ RepositoryPushed 구독
```

### EventBus는 중앙 실행기가 아니다

EventBus는 다음을 알거나 직접 실행하지 않는다.

- Git Provider와 Webhook 인증
- Pipeline 단계와 Task 순서
- Plugin 선택과 Generator 호출
- 파일 생성과 검증
- 재시도와 Timeout
- Commit, Push와 Notification 정책

EventBus는 Generic Event의 구독, 구독 해제와 비동기 전달만 담당한다.

### Pipeline은 명시적인 실행 순서를 소유한다

전체 업무 흐름을 Handler 사이의 Event 연쇄에만 숨기지 않는다.

```text
GenerationPipeline
  1. ValidateSpecificationTask
  2. ResolvePluginsTask
  3. PrepareWorkspaceTask
  4. PlanGenerationTask
  5. GenerateTask
  6. ValidateProjectTask
  7. BuildTask
  8. DeliveryTask
```

Pipeline이 소유하는 정책:

- Task 순서와 성공 조건
- 실패 시 중단 여부
- Timeout과 재시도
- 취소와 정리
- Git 전달 가능 조건

각 단계는 시작, 완료와 실패 Event를 발행한다. Event는 흐름을 관찰하고 다른
컴포넌트와 연결하지만 Pipeline의 순서를 대신하지 않는다.

### Handler가 Event를 업무 동작에 연결한다

Handler는 얇은 Application Adapter다.

```python
class PipelineRequestedHandler:
    def __init__(
        self,
        pipeline_service: PipelineService,
        event_publisher: EventPublisher,
    ) -> None:
        self._pipeline_service = pipeline_service
        self._event_publisher = event_publisher

    async def handle(self, event: RepositoryPushedEvent) -> None:
        result = await self._pipeline_service.start(event)
        await self._event_publisher.publish(
            PipelineStartedEvent(
                job_id=result.job_id,
                pipeline_id=result.pipeline_id,
            )
        )
```

EventBus는 `PipelineService`를 모른다. 어떤 Event가 어떤 업무를 시작하는지는
Application의 Handler 조립에서 결정한다.

## 3. Command와 Event

모든 메시지를 Event라고 부르면 요청과 이미 발생한 사실을 구분하기 어렵다.

### Command

어떤 동작을 수행해 달라는 요청이다.

```text
RequestPipelineRun
GenerateProject
ValidateProject
CommitGeneratedChanges
SendNotification
```

Command는 일반적으로 하나의 책임 있는 Handler가 처리한다. 요청됐다는 사실이
성공을 의미하지 않는다.

### Event

이미 발생한 사실이며 과거형으로 이름을 작성한다.

```text
RepositoryPushed
PipelineStarted
TaskCompleted
GenerationFailed
GitCommitCompleted
NotificationSent
```

Event는 여러 Handler가 구독할 수 있다.

현재 `EventBus`는 Event만 다룬다. 6단계 구현 전 다음 중 하나를 별도로
결정한다.

1. CommandBus와 EventBus 분리
2. 하나의 Message Transport 위에 Command/Event API 분리

Command를 여러 Handler에 broadcast하는 구조는 기본값으로 채택하지 않는다.
결정 전까지 Command와 Event를 섞은 이름을 대량 구현하지 않는다.

## 4. 기준 실행 흐름

### Webhook

```text
GitHub
  → Webhook Adapter
  → 서명 검증
  → Payload를 내부 데이터로 정규화
  → 중복 Delivery 검사
  → RepositoryPushed 발행
  → HTTP 요청은 접수 결과 반환
```

Webhook HTTP Handler 안에서 생성, Build, Commit과 Push를 실행하지 않는다.

### Pipeline

```text
RepositoryPushed
  → Pipeline 요청 Handler
  → GenerationJob 생성
  → GenerationPipeline 시작
  → PipelineStarted 발행
```

### Task

```text
Pipeline
  → TaskStarted 발행
  → Task.execute()
  → TaskCompleted 또는 TaskFailed 발행
```

동일 프로세스의 Pipeline은 Task 결과를 직접 받아 다음 단계를 결정한다.
Event만 기다리며 다음 순서를 추측하지 않는다. 향후 분산 Task 실행이
필요해지면 Command와 결과 Event 경계를 도입할 수 있지만 다음 단계의 결정
주체는 하나로 유지한다.

### Plugin과 Generator

```text
GenerateTask
  → Catalog/Registry에서 Generator Plugin 선택
  → Plugin 실행
  → Generator가 Plan 작성
  → Applier가 Workspace 적용
  → Manifest 저장
  → GenerationCompleted 또는 GenerationFailed
```

EventBus가 Plugin을 조회하거나 Generator를 호출하지 않는다.

### 검증과 Git

```text
ValidateTask
  → Import/Test/Lint/Build
  → ValidationCompleted

Pipeline
  → 필수 검증 성공 확인
  → DeliveryTask 실행

DeliveryTask
  → Branch → Commit → Push → Pull Request
  → GitCommitCompleted / PullRequestCreated
```

Git 전달 가능 조건은 Pipeline 정책이 소유한다.

## 5. Event 분류

아래 목록은 Naming과 범주를 확정한 것이며 미리 빈 클래스를 만들라는 뜻이
아니다. 실제 Producer와 Consumer가 생길 때 테스트와 함께 구현한다.

```text
Repository/Webhook
  WebhookReceived
  WebhookRejected
  RepositoryPushed
  RepositoryDeliveryIgnored

Job/Pipeline
  GenerationJobCreated
  PipelineStarted
  PipelineCompleted
  PipelineFailed
  PipelineCancelled

Task
  TaskStarted
  TaskCompleted
  TaskFailed
  TaskRetryScheduled

Plugin
  PluginResolved
  PluginExecutionStarted
  PluginExecutionCompleted
  PluginExecutionFailed

Generation/Manifest
  GenerationPlanned
  GenerationCompleted
  GenerationFailed
  GenerationConflictDetected
  ManifestStored

Validation/Build
  ValidationStarted
  ValidationStepCompleted
  ValidationCompleted
  ValidationFailed
  BuildCompleted
  BuildFailed

Git/Delivery
  RepositoryCheckedOut
  BranchCreated
  GitCommitCompleted
  GitPushCompleted
  PullRequestCreated
  DeliveryFailed

Notification/Observation
  NotificationSent
  NotificationFailed
  AuditRecordRequested
  MetricRecorded
```

## 6. Event Envelope

현재 `Event`는 다음 공통 정보를 가진 불변 dataclass다.

```text
event_id       Event 고유 ID
event_type     직렬화 가능한 Event 종류
event_version  Payload Schema 버전
created_at     timezone-aware UTC 발생 시각
correlation_id 하나의 Job/Delivery 전체 흐름 ID
causation_id   직접 원인이 된 Message ID
job_id         관련 GenerationJob ID
producer       논리적인 발생 컴포넌트
payload        Event별 불변 데이터
```

원칙:

- Event ID, 시간과 Payload는 발행 후 변경하지 않는다.
- 열린 파일, DB Session, Plugin 인스턴스 같은 실행 객체를 Payload에 넣지 않는다.
- Password, Token, Webhook Secret과 인증 Header를 넣지 않는다.
- 경로는 가능한 Workspace 상대경로와 식별자로 표현한다.
- Schema 변경은 `event_version`으로 관리한다.
- `correlation_id`는 전체 흐름, `causation_id`는 인과관계를 추적한다.

`event_type`은 구체 Event 클래스 이름에서 계산하고, 나머지 metadata는 생성 시
확정한다. `correlation_id`가 생략되면 자신의 `event_id`를 사용한다. Event payload의
외부 transport 직렬화 계약은 아직 별도 구현하지 않았다.

## 7. Delivery와 Handler 의미

### 현재 보장

```text
Delivery       in-process
Durability     없음
Replay         없음
Ordering       보장하지 않음
Handler 실행   같은 Event의 Handler를 동시 실행
Failure        publish 호출자에게 예외 전파
```

현재 로컬 MVP에는 적절하지만 장기 보장으로 간주하지 않는다.

### Handler 순서에 의존하지 않는다

같은 Event의 Handler는 서로 독립적이어야 한다.

```text
GenerationCompleted
  ├── Audit Handler
  ├── Metrics Handler
  └── Status Projection Handler
```

순차 업무는 Pipeline 또는 하나의 Application Handler가 명시적으로 조정한다.

### 실패 분류

```text
Critical Handler
  상태 전이에 필요
  실패 시 Command/Pipeline 실패 가능

Observational Handler
  Logging, Metrics, Audit Projection
  핵심 업무 실패와 별도 정책 필요
```

Generic EventBus가 Handler 이름을 보고 중요도를 판단하지 않는다. 구독 Metadata
또는 상위 Dispatcher 정책으로 명시한다.

현재 구독은 `HandlerFailurePolicy.CRITICAL` 또는 `OBSERVATIONAL`을 명시한다.
기본값은 하위 호환성을 위해 critical이다. Dispatcher는 동일 Event의 모든 handler를
동시에 끝까지 실행하고, critical 실패가 하나라도 있으면 전체 실패 목록을 포함한
`EventDispatchError`를 발생시킨다. observational 실패만 있으면 publish는 정상
반환하되 `EventDispatchResult.failures`에 결과를 남긴다. EventBus는 handler 이름이나
업무 종류를 보고 정책을 추측하지 않는다.

### 중복 처리

외부 Transport의 최소 한 번 전달에서는 같은 Event가 재전달될 수 있다.
외부 상태를 변경하는 Handler는 `event_id`나 업무 Idempotency Key로 중복
실행에 안전해야 한다.

## 8. In-process Bus와 외부 Transport

Core는 Redis, Kafka, RabbitMQ 같은 제품을 직접 알지 않는다.

```text
Application Producer
  → EventPublisher Protocol
       ├── InProcessEventBus
       └── DurableEventTransport Adapter
              ├── Serialization
              ├── Queue/Broker
              ├── Retry/Dead-letter
              └── Consumer
```

분산 요구가 실제로 생길 때 다음을 추가한다.

- EventPublisher Protocol
- Serializer와 Schema Registry
- Infrastructure Transport Adapter
- Consumer 수명주기
- Retry와 Dead-letter
- Outbox/Inbox 또는 동등한 원자성 정책

현재 EventBus를 미리 특정 Broker Wrapper로 바꾸지 않는다.

## 9. 직접 호출과 Event의 선택

모든 함수 호출을 Event로 바꾸지 않는다.

직접 호출이 적합한 경우:

- 같은 유스케이스에서 즉시 결과가 필요
- 순서와 실패가 호출 스택에 보여야 함
- 객체 내부 계산과 검증
- Generator의 `render()`와 `plan()`

Event가 적합한 경우:

- Producer가 Consumer를 몰라야 함
- 하나의 사실을 여러 Consumer가 관찰
- 컴포넌트나 프로세스 경계를 넘음
- 비동기 후속 처리 가능
- Audit과 상태 추적 필요

Event-driven은 직접 호출을 금지하는 설계가 아니다.

## 10. 상태의 Source of Truth

EventBus 메모리를 Job 상태 저장소로 사용하지 않는다.

```text
Event      = 발생한 사실
Job Store  = 현재 Job 상태의 Source of Truth
Manifest   = 파일 생성 결과의 Source of Truth
Git        = 전달된 코드 변경의 Source of Truth
Projection = Event로 갱신되는 조회 상태
```

중요 상태 전이는 Idempotent하게 저장하고 재조회할 수 있어야 한다.

현재 Core에는 `JobStore` async Protocol이 있고 로컬 CLI와 테스트를 위한
`InMemoryJobStore`, 제어면 서버를 위한 `PostgreSQLJobStore` adapter가 있다. 두
adapter 모두 예상 이전 상태를 비교하여 동일 Job의 경쟁 상태 전이를 거부한다.
InMemory adapter는 재시작 후 복구되지 않으므로 분산 실행에는 PostgreSQL을 사용한다.

PostgreSQL adapter는 구현됐다. unique idempotency key의 원자적 claim, status CAS와
revision, JSONB snapshot을 제공한다. AuditSink도 event_id primary key로 중복 append를
막는다. 상세 schema와 실제 동시성 검증은 `control_plane_persistence.md`를 따른다.
인증된 Trigger/Status HTTP adapter도 구현됐다. Trigger는 재실행 가능한 상대경로
submission과 specification hash를 먼저 저장하고, 신규 claim일 때만
`GenerationJobCreatedEvent`를 발행한다. HTTP 요청 안에서는 Pipeline을 실행하지
않는다.

JobStore의 실행 lease, heartbeat와 stale-worker fencing은 구현됐다. pending 상태의
만료 lease만 takeover하며, generating/validating 중 만료된 Job은 부분 Workspace를
추측해서 이어 실행하지 않고 `JobLeaseExpired` failed로 복구한다. lease worker와
Generation Pipeline도 연결됐다. worker는 HTTP 요청과 분리되어 claimed Job의 명세
hash를 재검증하고 실행 중 heartbeat를 유지한다. 장기 polling loop와 graceful shutdown
운영 adapter는 다음 단계다.

`GenerationJobStateMachine`은 다음 전이만 허용한다.

```text
pending → generating → validating → succeeded
    └──────── 각 실행 상태에서 ────────→ failed
```

각 전이는 기존 snapshot을 변경하지 않고 전체 Pydantic 불변조건을 다시 검증한 새
snapshot을 만든다. Application Service는 새 상태를 JobStore에 먼저 저장하고 저장에
성공한 사실을 Event로 발행해야 한다.

## 11. 계층과 금지 사항

```text
Core
  Event 계약, Publisher/Handler와 Pipeline/Task 계약

Application
  Handler, Pipeline 조정, 유스케이스와 상태 전이

Services
  Generation, Validation, Build, Git 유스케이스

Infrastructure
  Webhook, Process, File, Git Provider, Broker Adapter
```

금지:

- Core EventBus가 Infrastructure를 import
- EventBus가 PluginManager나 Generator를 소유
- Webhook 요청 안에서 Pipeline 전체 실행
- Generator가 Git 구현을 import
- Handler 등록 순서로 Pipeline 순서 표현
- Event Payload에 비밀정보나 실행 객체 포함

## 12. 현재 구현 평가

현재 구현:

- 불변 Event와 ID, timezone-aware UTC 시각, schema version
- correlation/causation, job과 producer metadata
- Event 타입별 Handler 등록과 해제
- typed Handler 계약과 구독 목록 snapshot
- 비동기 publish
- Git, Plugin, Generator와 독립적인 Core
- 명시적 Task 순서의 SequentialPipeline
- Task별 timeout, 제한된 retry, 실패 중단과 cancellation
- Pipeline/Task lifecycle Event
- critical/observational 구독 실패 정책과 구조화된 dispatch 결과
- envelope-only Logging/Audit Handler와 async AuditSink Protocol
- 로컬·테스트용 append-only InMemoryAuditSink

추후 필요:

- Application Handler 조립
- PostgreSQL AuditSink와 외부 전달 중복 방지
- 외부 Transport가 필요할 때의 Protocol

현재 구현은 폐기 대상이 아니라 최소 기반이다.

## 13. 구현 순서

1. Core Event 계약 안정화: 완료
   - 불변성과 공통 Metadata
   - Typed Handler
   - 구독 캡슐화
2. Generic Pipeline Core: 완료
   - 명시적 Task 순서
   - timeout, retry, 실패와 cancellation
   - Pipeline/Task lifecycle Event
3. Job lifecycle 기반: 완료
   - Job, Generation, Validation Event
   - 상태 머신, JobStore Protocol과 로컬 adapter
4. 첫 Application 수직 Event 흐름: 완료
   - Prepare, Generate와 Validate Task
   - 기존 Generator, ManifestStore와 ProjectValidator 연결
   - JobStore 선저장 후 lifecycle Event 발행
   - import, pytest, Ruff와 wheel build 성공 후 Job succeeded
5. 관찰 Handler
   - Logging, Audit, Metrics, Job 상태 Projection
6. Git과 Webhook 연결
   - Webhook 정규화와 중복 방지
   - Repository와 Git Delivery Event
7. 필요할 때 외부 Transport
   - 직렬화, Idempotency, Retry, Dead-letter, Outbox/Inbox

## 14. 변경 승인 기준

다음과 같은 실제 필요가 있을 때 EventBus 구현을 바꾼다.

- Pipeline Event를 현재 API로 안전하게 표현할 수 없음
- Handler 오류가 다른 업무를 잘못 실패시킴
- Correlation/Causation 추적이 필요
- 프로세스 경계를 넘어야 함
- 재시작 후 Delivery나 Replay가 필요
- 테스트에서 상태 노출이나 실행 순서 문제가 확인됨

미래 Broker를 추측하거나 event-driven처럼 보이기 위해 재작성하지 않는다.

## 15. 최종 원칙

1. EventBus는 AutoForge의 중앙 통신 메커니즘이다.
2. EventBus는 업무 로직과 실행 순서를 소유하지 않는다.
3. Pipeline은 Job 내부 Task 순서와 실패 정책을 소유한다.
4. Handler는 Event와 Application Service를 연결한다.
5. 주요 상태 변화는 Event로 표현할 수 있어야 한다.
6. 모든 내부 함수 호출을 Event로 바꾸지는 않는다.
7. Command 요청과 Event 사실을 구분한다.
8. Event Payload는 불변이며 비밀정보와 실행 객체를 포함하지 않는다.
9. Handler 등록 순서에 업무 순서를 의존하지 않는다.
10. 외부 Transport는 Core 계약과 Infrastructure Adapter로 분리한다.
11. 외부 상태를 바꾸는 Handler는 중복 전달에 안전해야 한다.
12. 현재 in-process EventBus는 이유 없이 재작성하지 않고 점진적으로 확장한다.
