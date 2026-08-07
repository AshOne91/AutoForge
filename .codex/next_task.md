# 다음 작업

전체 배경과 현재 구조는 `docs/PROJECT_GUIDE_2026-07-29.md`와
`docs/architecture/event_driven_architecture.md`를 먼저 읽는다.

## 완료된 기반

- Store별 Alembic Global/Shard migration
- KIS Account/Profile shard 저장과 API 2대 교차 검증
- Redis Cluster 3 Primary + 3 Replica와 primary 장애 전환
- RabbitMQ transport, Transactional Outbox Relay와 Processed Message Inbox
- KIS Profile event의 broker 장애 복구와 중복 전달 안전성 검증

## 완료: Event와 Pipeline 실행 계층

EventBus는 프로세스 내부의 generic 비동기 전달만 담당하며 Git, Generator,
Plugin 또는 Pipeline 업무 규칙을 알지 않는다. RabbitMQ는 프로세스 외부 durable
transport이며 EventBus를 대체하지 않는다.

완료된 구현은 다음과 같다.

1. Generation Job lifecycle event와 실패 event 계약
2. 명시적 task 순서, timeout, retry, 실패와 cancellation 정책
3. Prepare → Generate → Validate Application Pipeline
4. JobStore 선저장 후 lifecycle event 발행
5. import, pytest, Ruff와 wheel build 성공 조건

## 현재 목표: 관찰과 영속 Job 실행

완료:

1. 구조화된 logging handler
2. envelope-only append-only audit record와 InMemory adapter
3. critical/observational handler 실패 정책
4. KIS Generation Pipeline 전체 실사용 검증

완료:

1. PostgreSQL JobStore와 status CAS/revision
2. PostgreSQL AuditSink와 event_id 중복 방지
3. unique idempotency key 기반 원자적 Job claim
4. 실제 PostgreSQL 16에서 두 store 인스턴스 경쟁 검증

다음:

완료:

1. idempotency key 기반 trigger/status Application API
2. Bearer 인증, streaming 요청 크기 제한과 source/output root 경로 제한
3. 재시작 가능한 relative-path submission snapshot과 key 재사용 충돌 검증
4. 실제 API 인스턴스 2대에서 같은 trigger의 단일 PostgreSQL Job 생성 검증

다음:

완료:

1. pending Job의 lease claim과 만료 takeover
2. heartbeat/release와 lease token 기반 상태 쓰기 fencing
3. generating/validating 중 만료 Job의 `JobLeaseExpired` failed 복구
4. 실제 PostgreSQL 16 worker 경쟁, heartbeat, takeover와 stale token 차단 검증

다음:

완료:

1. pending Job을 HTTP 요청과 분리된 worker가 claim해 기존 Generation Pipeline에 전달
2. claimed 명세 hash 재검증과 source/output root 경로 복원
3. Pipeline 실행 중 heartbeat 유지와 모든 상태 전이의 lease token fencing
4. terminal 상태 lease 정리와 입력 소실·명세 변경의 failed 처리
5. 실제 PostgreSQL worker 2대 경쟁에서 단일 Generation Pipeline 실행 검증

다음:

완료:

1. idle polling, error backoff와 주기적 abandoned sweep 운영 loop
2. stop event 이후 새 claim 중단과 현재 Pipeline grace period
3. grace 초과 시 Pipeline·heartbeat 취소 및 lease 만료 복구 위임
4. SIGINT/SIGTERM의 async stop event 변환과 기존 handler 복원
5. 실제 PostgreSQL validating Job 중단·만료·failed 복구 검증

다음:

완료:

1. infrastructure-independent Git Provider checkout 계약
2. HTTPS/canonical SSH host allowlist와 embedded credential 금지
3. test-only local root, 안전한 revision과 Workspace destination 검증
4. system/global config와 interactive credential prompt 차단
5. exact commit detached checkout, clean 상태와 원본 repository 불변 검증

다음:

완료:

1. GenerationJob submission에 repository/ref를 추가하고 claimed worker가 Job별
   IsolatedWorkspace에 checkout하도록 연결한다.
2. checkout repository 내부에서만 Generation/Validation Pipeline을 실행한다.
3. 실패 Workspace 보존 정책과 정리 후 원본 repository 불변성을 검증한다.

다음:

완료:

1. 검증 성공 결과에만 작업 branch와 commit을 허용하는 Core 계약과 adapter 기반
2. 생성기가 변경할 수 있는 경로 allowlist와 예상 밖 변경·rename/copy 거부
3. expected base SHA fencing, author, commit message와 signing fingerprint 정책
4. 변경이 없을 때 branch와 빈 commit을 만들지 않는 동작

다음:

완료:

1. GenerationJob에 `validating → committing → succeeded` 수명주기 추가
2. manifest의 created/changed 파일과 `.autoforge/manifest.json` 기반 allowlist 계산
3. 원격 worker의 검증 후 안전 commit 실행과 결과 Job 저장
4. commit 실패의 failed 상태 저장과 lease 만료 복구
5. GitCommitStarted/Completed/FailedEvent 발행
6. 실제 생성 repository의 성공 commit과 예상 밖 변경 거부 종단 검증

다음:

완료:

1. credential을 URL·명령 인자·helper 파일에 노출하지 않는 Secret Provider 계약
2. 검증된 commit만 작업 branch에 보내는 non-force push adapter
3. 작업 branch prefix allowlist와 protected branch 직접 push 금지
4. 동일 SHA push 멱등 처리와 non-fast-forward 거부
5. 실제 bare remote와 기록용 runner를 이용한 push·credential 비노출 검증

다음:

1. GenerationJob에 `pushing` 상태와 GitPushResult를 추가한다.
2. 원격 worker가 commit 성공 후 push하고 실패를 failed Job/Event로 저장한다.
3. PostgreSQL status migration과 worker 2대 fencing을 검증한다.
4. 그다음 Pull Request adapter와 protected branch 정책을 연결한다.

## 후속 목표

1. Airflow 기반 News 수집/RAG 적재 workflow
2. Git checkout/branch/검증/commit/push/PR plugin
3. GitHub Webhook 서명 검증과 delivery 중복 방지
4. GitHub Actions, Docker build와 AWS 배포 계약
5. RabbitMQ HA, AWS Redis/DB Multi-AZ와 전체 장애·보안 검증

빈 미래 디렉터리를 미리 만들지 않는다. 각 단계에 진입할 때 구현 파일과 테스트를
함께 생성하고, KIS 실제 사용 사례로 계약을 검증한다.
## Current next task (updated 2026-08-07)

The `pushing` lifecycle, `GitPushResult` persistence, worker-to-push-adapter
connection, failure events, abandoned-job recovery, and PostgreSQL status migration
are complete.

The next bounded Git-automation step is to define and verify the Pull Request
contract and protected-branch policy. Do not implement webhook, deployment, or AI
generation as part of that step. The older sequential checklist below is retained
as implementation history and is superseded where it still labels push work as
pending.

## Current next task (updated after Git composition, 2026-08-07)

Pull Request 계약, 보호 branch 정책, GitHub HTTP adapter, GenerationJob lifecycle와
Git automation composition root까지 완료했다. 이전 문단에서 Pull Request를 다음
작업으로 표시한 내용은 구현 이력이며 이 문단이 대체한다.

다음 한정된 단계는 실제 worker/server 실행 진입점이다.

1. 검증된 설정에서 PostgreSQL JobStore와 기존 Generation Pipeline을 조립한다.
2. `GitAutomationComponents`가 존재할 때만 Git/PR 의존성을 worker에 주입한다.
3. worker loop 시작과 종료 시 HTTP/DB resource 수명주기를 명시적으로 관리한다.
4. 설정이 비활성화된 로컬 실행과 기존 CLI 호환성을 유지한다.

Webhook, 배포, AI 생성은 이 단계에 포함하지 않는다.

## Current next task (updated after Worker CLI, 2026-08-07)

PostgreSQL 기반 Worker composition과 실제 `autoforge worker` 실행 진입점, 종료
signal 및 HTTP/DB resource 수명주기 관리는 완료했다. 바로 앞 문단의 worker 항목은
완료 이력이며 이 문단이 현재 작업을 대체한다.

다음 한정된 단계는 기존 인증형 GenerationJob HTTP API의 Control Plane 서버
composition과 실행 진입점이다.

1. PostgreSQL engine과 JobStore, EventBus, `GenerationSubmissionService` 및 기존
   FastAPI app을 조립한다.
2. API bearer token과 PostgreSQL URL은 명령행 값이 아닌 환경변수 참조로 받는다.
3. FastAPI/서버 종료 시 DB engine을 명시적으로 dispose한다.
4. HTTP 요청은 Job 제출만 담당하고 Generation Pipeline은 별도 worker에서 실행하는
   현재 수평 확장 경계를 유지한다.
5. 기존 로컬 `generate`, `version`, `plugin`, `worker` 명령 호환성을 검증한다.

Webhook 서명 검증, 배포, AI 생성과 메시지 브로커 확장은 이 단계에 포함하지 않는다.
