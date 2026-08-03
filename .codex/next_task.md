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

1. credential을 URL·명령 인자에 노출하지 않는 Secret Provider 계약을 구현한다.
2. 검증된 commit만 remote 작업 branch에 non-force push하는 계약을 구현한다.
3. protected branch 직접 push를 금지하고 Pull Request adapter 경계를 구현한다.

## 후속 목표

1. Airflow 기반 News 수집/RAG 적재 workflow
2. Git checkout/branch/검증/commit/push/PR plugin
3. GitHub Webhook 서명 검증과 delivery 중복 방지
4. GitHub Actions, Docker build와 AWS 배포 계약
5. RabbitMQ HA, AWS Redis/DB Multi-AZ와 전체 장애·보안 검증

빈 미래 디렉터리를 미리 만들지 않는다. 각 단계에 진입할 때 구현 파일과 테스트를
함께 생성하고, KIS 실제 사용 사례로 계약을 검증한다.
